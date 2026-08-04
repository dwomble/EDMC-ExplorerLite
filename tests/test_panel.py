"""
Unit tests for the compact panel (explorer/ui/panel.py) and prefs (explorer/ui/prefs.py).

Run with:
    .venv/bin/python -m pytest tests/test_panel.py -v --tb=short

`harness` (session-scoped, one shared Tk root for the whole test run) comes from
conftest.py -- see its docstring for why.
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

    reset_plugin_modules()
    from load import plugin_start3, plugin_app, plugin_stop, journal_entry
    plugin_start3(str(harness.plugin_dir))
    plugin_app(harness.parent)

    harness.journal_handlers.clear()
    harness.register_journal_handler(journal_entry, "Testy", "Deltius", False)

    yield harness

    plugin_stop()
    harness.assert_no_unhandled_exceptions()

def _panel_lines(load) -> list[str]:
    return [child["text"] for child in load.panel.scroll.interior.winfo_children()]

class TestPanelStates:

    def test_idle_state_is_a_single_line(self, plugin:TestHarness) -> None:
        import load
        lines = _panel_lines(load)
        assert lines == ["Explorer — idle"]

    def test_honk_state_shows_counts_and_verdict(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        lines = _panel_lines(load)
        assert lines[0] == "QuietSpace — 1 bodies, 0 signals"
        assert lines[1] == "Honk: probably quiet"

    def test_full_walkthrough_shows_flagged_bodies_section(self, plugin:TestHarness) -> None:
        plugin.config.set("EDMCExplorerLite_ScanValueThreshold", 50000)
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        import load
        lines = _panel_lines(load)
        assert lines[0].startswith("Deltius —")
        assert any("above threshold" in line for line in lines)

class TestPrefs:

    def test_build_and_save_roundtrip(self, plugin:TestHarness) -> None:
        from explorer.ui import prefs as prefs_ui
        from explorer.constants import CFG_SCAN_VALUE_THRESHOLD, CFG_OVERLAY_ENABLED

        frame = prefs_ui.build_prefs(plugin.parent, "Testy", False)
        assert frame is not None

        prefs_ui._scan_threshold_var.set("123456")
        prefs_ui._overlay_enabled_var.set(False)
        prefs_ui.save_prefs("Testy", False)

        assert plugin.config.get_int(CFG_SCAN_VALUE_THRESHOLD) == 123456
        assert plugin.config.get_bool(CFG_OVERLAY_ENABLED) is False

    def test_invalid_threshold_falls_back_to_default(self, plugin:TestHarness) -> None:
        from explorer.ui import prefs as prefs_ui
        from explorer.constants import CFG_EXOBIO_VALUE_THRESHOLD, DEFAULT_EXOBIO_VALUE_THRESHOLD

        prefs_ui.build_prefs(plugin.parent, "Testy", False)
        prefs_ui._exobio_threshold_var.set("not-a-number")
        prefs_ui.save_prefs("Testy", False)

        assert plugin.config.get_int(CFG_EXOBIO_VALUE_THRESHOLD) == DEFAULT_EXOBIO_VALUE_THRESHOLD

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
