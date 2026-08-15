"""
Unit tests for the overlay system summary (explorer/ui/overlay_summary.py).

Run with:
    .venv/bin/python -m pytest tests/test_overlay_summary.py -v --tb=short

`harness` (session-scoped, one shared Tk root) comes from conftest.py -- the default overlay
mode ('Modern') is already active, no per-test marker needed.
"""
import pytest
from typing import Generator

from harness import TestHarness, reset_plugin_modules
from explorer.ui.overlay_summary import FRAME_PREFIX, MAX_BODY_LINES

@pytest.fixture
def plugin(harness:TestHarness, tmp_path, monkeypatch) -> Generator[TestHarness, None, None]:
    from explorer.state import state as explorer_state
    explorer_state.reset_all()

    import explorer.db.store as store_module
    monkeypatch.setattr(store_module, "resolve_db_path", lambda: tmp_path / "explorer.sqlite")

    import explorer.session_persist as session_persist_module
    monkeypatch.setattr(session_persist_module, "resolve_session_path", lambda: tmp_path / "session_state.json")

    reset_plugin_modules()
    from load import plugin_start3, plugin_app, plugin_stop, journal_entry
    plugin_start3(str(harness.plugin_dir))
    plugin_app(harness.parent)

    harness.journal_handlers.clear()
    harness.register_journal_handler(journal_entry, "Testy", "Deltius", False)

    yield harness

    plugin_stop()
    harness.assert_no_unhandled_exceptions()

class TestSystemSummaryOverlay:

    def test_render_is_a_safe_noop_with_no_system_known_yet(self, plugin:TestHarness) -> None:
        import load
        assert load.summary_overlay is not None and load.store is not None
        load.summary_overlay.render(load.store, load.explorer_state) # must not raise
        assert load.summary_overlay.overlay._overlay.messages == {}

    def test_render_shows_header_and_flagged_body_lines(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None and load.panel is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)

        load.summary_overlay.render(load.store, load.explorer_state)

        messages = load.summary_overlay.overlay._overlay.messages
        header = messages[f"{FRAME_PREFIX}header"]
        assert header[1] == "QuietSpace — 1 body — done" # matches panel.py's system_header_line()

        body_line = messages[f"{FRAME_PREFIX}body-0"]
        assert body_line[1].startswith("A 1")
        assert "1M Cr" in body_line[1]

    def test_render_caps_body_lines_and_shows_an_overflow_count(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None
        for body_id in range(1, MAX_BODY_LINES + 3):
            body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, body_id, f"QuietSpace A {body_id}")
            load.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)

        load.summary_overlay.render(load.store, load.explorer_state)

        messages = load.summary_overlay.overlay._overlay.messages
        assert f"{FRAME_PREFIX}body-{MAX_BODY_LINES - 1}" in messages
        assert f"{FRAME_PREFIX}body-{MAX_BODY_LINES}" not in messages
        assert messages[f"{FRAME_PREFIX}overflow"][1] == "+2 more"

    def test_render_respects_summary_disabled_config(self, plugin:TestHarness) -> None:
        from explorer.constants import CFG_OVERLAY_SUMMARY_ENABLED

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)
        plugin.config.set(CFG_OVERLAY_SUMMARY_ENABLED, False)

        import load
        assert load.store is not None and load.summary_overlay is not None
        load.summary_overlay.render(load.store, load.explorer_state)

        assert load.summary_overlay.overlay._overlay.messages == {}

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
