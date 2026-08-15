"""
Unit tests for the history popup (explorer/ui/history_view.py) and store.get_history_tree().

Run with:
    .venv/bin/python -m pytest tests/test_history_view.py -v --tb=short

`harness` (session-scoped, one shared Tk root) comes from conftest.py.
"""
import pytest
from typing import Generator

from harness import TestHarness, reset_plugin_modules

@pytest.fixture
def plugin(harness:TestHarness, tmp_path, monkeypatch) -> Generator[TestHarness, None, None]:
    from explorer.state import state as explorer_state
    explorer_state.reset_all()

    import explorer.db.store as store_module
    monkeypatch.setattr(store_module, "resolve_db_path", lambda: tmp_path / "explorer.sqlite")

    import explorer.session_persist as session_persist_module
    monkeypatch.setattr(session_persist_module, "resolve_session_path", lambda: tmp_path / "session_state.json")

    from explorer.constants import CFG_SCAN_VALUE_THRESHOLD
    harness.config.set(CFG_SCAN_VALUE_THRESHOLD, 50000)

    reset_plugin_modules()
    from load import plugin_start3, plugin_app, plugin_stop, journal_entry
    plugin_start3(str(harness.plugin_dir))
    plugin_app(harness.parent)

    harness.journal_handlers.clear()
    harness.register_journal_handler(journal_entry, "Testy", "Deltius", False)

    yield harness

    plugin_stop()
    harness.assert_no_unhandled_exceptions()

class TestHistoryTreeQuery:

    def test_history_tree_matches_walkthrough(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        import load
        assert load.store is not None and load.explorer_state.cmdr_id is not None
        tree = load.store.get_history_tree(load.explorer_state.cmdr_id)

        assert len(tree) == 1
        system = tree[0]
        assert system["name"] == "Deltius"
        assert system["status"] == "sold"

        bodies = {b["name"]: b for b in system["children"]}
        assert "Deltius A 2" in bodies
        species = bodies["Deltius A 2"]["children"]
        assert len(species) == 1
        assert species[0]["name"] == "Bacterium Aurasus"
        assert species[0]["status"] == "sold"
        # actual_value is now the sample's own confirmed_value (an estimate), not BioData's
        # exact per-item Value+Bonus -- see handlers_exobiology.on_sell_organic_data's docstring.
        assert species[0]["actual_value"] == 1_000_000

class TestHistoryViewPopup:

    def test_open_populates_tree_and_summary(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        import load
        assert load.history_view is not None
        load.history_view.open()

        assert load.history_view.window is not None
        assert load.history_view.window.winfo_exists()
        assert load.history_view.summary_label is not None
        assert "Exobiology: 5M Cr" in load.history_view.summary_label["text"]

        assert load.history_view.tree is not None
        systems = load.history_view.tree.get_children()
        assert len(systems) == 1
        bodies = load.history_view.tree.get_children(systems[0])
        assert len(bodies) >= 1

        load.history_view._on_close()

    def test_refresh_without_open_window_is_a_safe_noop(self, plugin:TestHarness) -> None:
        import load
        assert load.history_view is not None
        load.history_view.refresh() # never opened -- must not raise

    def test_panel_history_button_opens_the_popup(self, plugin:TestHarness) -> None:
        import load
        assert load.panel is not None
        load.panel._open_history()

        assert load.history_view is not None
        assert load.history_view.window is not None
        load.history_view._on_close()

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
