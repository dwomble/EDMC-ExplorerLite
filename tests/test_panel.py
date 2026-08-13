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

    def test_flagged_body_shows_before_full_system_fss_sweep(self, plugin:TestHarness) -> None:
        """
        Regression test: flagged bodies (value/exobio) used to be gated behind
        FSSAllBodiesFound, so a body scanned directly (without sweeping the whole system map
        first) never showed up. This sequence never fires FSSAllBodiesFound at all.
        """
        plugin.config.set("EDMCExplorerLite_ScanValueThreshold", 50000)
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("partial_scan_no_full_fss", 0.02)

        import load
        lines = _panel_lines(load)
        assert any(line.startswith("Honk:") for line in lines)
        assert any("above threshold" in line for line in lines)

    def test_star_only_system_says_dss_not_required(self, plugin:TestHarness) -> None:
        """ A system with no planets at all (e.g. a bare binary) shouldn't read as "checked,
        nothing found" -- there was never anything to DSS in the first place. """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("binary_star_only_system", 0.02)

        import load
        lines = _panel_lines(load)
        assert any("DSS not required" in line for line in lines), lines
        assert not any("Nothing flagged" in line for line in lines), lines

    def test_exobio_line_shows_progress_then_drops_once_done(self, plugin:TestHarness) -> None:
        """
        Regression test for the progressive-detail redesign: a flagged body's exobio line
        should read as a generic "genus ~value" guess, become "species — N/3, value" once
        sampling starts, and disappear once that genus is fully sampled -- not keep showing a
        stale "exobio~9M Cr" label throughout.
        """
        plugin.load_events("explorer_events.json")
        events = plugin.events["full_walkthrough"]

        # "Log" and "Sample" ScanType both count as real samples (see SAMPLE_SCAN_TYPES in
        # handlers_exobiology.py) -- stop after the 2nd one (Log, then the first Sample) for 2/3.
        increments_seen:int = 0
        cutoff:int = len(events)
        for i, event in enumerate(events):
            if event.get("event") == "ScanOrganic" and event.get("ScanType") in ("Log", "Sample"):
                increments_seen += 1
                if increments_seen == 2:
                    cutoff = i + 1
                    break

        for event in events[:cutoff]:
            plugin.fire_event(event)

        import load
        lines = _panel_lines(load)
        assert any("Bacterium Aurasus — 2/3, 1M Cr" in line for line in lines)

        for event in events[cutoff:]:
            plugin.fire_event(event)

        lines = _panel_lines(load)
        assert not any("Bacterium" in line for line in lines) # body 2's only genus is done -- dropped entirely
        # The on-body exobiology section (header + "All species done here") should vanish too,
        # not linger once there's nothing left to sample -- not just the flagged-list line.
        assert not any("exobiology" in line for line in lines), lines

    def test_predicted_genus_line_is_superseded_by_confirmed_genus(self, plugin:TestHarness) -> None:
        """
        Regression test for the pre-DSS genus predictor: a landable body whose Scan properties
        match known genera's conditions should show a "N species ..." line (unconfirmed) in the
        system summary before any DSS data exists -- the species count itself isn't in doubt,
        only which genus it is, so no "?" on the count -- and the summary's "possible exobio"
        bucket should become "exobio potential" once SAASignalsFound confirms what's there.
        """
        plugin.load_events("explorer_events.json")
        events = plugin.events["predicted_then_confirmed"]

        confirm_index:int = next(i for i, e in enumerate(events) if e.get("event") == "SAASignalsFound")
        for event in events[:confirm_index]:
            plugin.fire_event(event)

        import load
        lines = _panel_lines(load)
        assert any(line.startswith("A 1 ") and "species" in line for line in lines), lines
        # Regression: a predicted-only (unconfirmed) body used to still count as "nothing
        # flagged" in the summary, printing that line right above the predicted body below it.
        assert not any("Nothing flagged" in line for line in lines), lines
        assert any("possible exobio" in line for line in lines), lines

        plugin.fire_event(events[confirm_index])

        lines = _panel_lines(load)
        assert not any("possible exobio" in line for line in lines), lines
        assert any("exobio potential" in line for line in lines), lines
        assert any(line.startswith("A 1 ") and "species" in line for line in lines), lines

    def test_known_bio_signals_count_even_without_dss_or_prediction(self, plugin:TestHarness) -> None:
        """
        Regression test: FSSBodySignals can confirm a body has biological signals well before
        it's DSS'd (SAASignalsFound) or even Scanned (so no genus_prediction guess exists yet
        either). Those bodies used to vanish from the flagged list entirely -- only the one
        body actually DSS'd in the system counted towards any summary line -- even though we
        already know for certain that other bodies in the system have biology too.
        """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("known_bio_signals_before_dss", 0.02)

        import load
        lines = _panel_lines(load)
        assert any("1 body exobio potential" in line for line in lines), lines
        assert any("2 bodies known biological signals" in line for line in lines), lines
        assert not any("possible exobio" in line for line in lines), lines # these are confirmed, not guessed
        assert any(line.startswith("A 1 ") and "biological signals" in line and "? Cr" in line for line in lines), lines
        assert any(line.startswith("A 3 ") and "biological signals" in line and "? Cr" in line for line in lines), lines

    def test_mapped_body_drops_off_the_list(self, plugin:TestHarness) -> None:
        """
        A value-flagged body with no biological interest should disappear from the flagged
        list once it's been mapped -- there's nothing left to do there, so it's no longer
        "of interest" (still visible in History, which is a permanent record, not a to-do list).
        """
        plugin.config.set("EDMCExplorerLite_ScanValueThreshold", 50000)
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("mapped_body_drops_off_list", 0.02)

        import load
        lines = _panel_lines(load)
        assert not any(line.startswith("A 1 ") for line in lines), lines

    def test_type_label_shown_on_flagged_body_line(self, plugin:TestHarness) -> None:
        plugin.config.set("EDMCExplorerLite_ScanValueThreshold", 50000)
        plugin.load_events("explorer_events.json")
        events = plugin.events["mapped_body_drops_off_list"]
        scan_index:int = next(i for i, e in enumerate(events) if e.get("event") == "Scan" and e.get("BodyID") == 1)
        for event in events[:scan_index + 1]:
            plugin.fire_event(event)

        import load
        lines = _panel_lines(load)
        assert any(line.startswith("A 1 MR ") for line in lines), lines

    def test_supercruise_exit_shows_exobiology_before_landing(self, plugin:TestHarness) -> None:
        """
        Dropping out of supercruise near a body should surface its predicted biology right
        away -- well before ApproachBody/Touchdown/on-foot -- so it's useful for deciding
        whether to land at all.
        """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("supercruise_exit_shows_bio_before_landing", 0.02)

        import load
        lines = _panel_lines(load)
        assert any("exobiology" in line for line in lines), lines
        assert any("species" in line for line in lines), lines

class TestNoDuplicateWidgets:
    """
    Regression test for a real bug: th.Base widgets (Button, Checkbutton, ...) only dedupe
    their light/dark pair in the overridden .grid() -- .pack() falls through to the generic
    proxy, which calls pack() on BOTH widgets, rendering the "History" button twice.
    """

    def test_history_button_is_gridded_not_packed(self, plugin:TestHarness) -> None:
        import load
        managers = {load.panel.history_button.obj.winfo_manager(), load.panel.history_button.alt.winfo_manager()}
        assert managers == {"grid", ""} # exactly one of the light/dark pair is actually placed

class TestPrefs:

    def test_build_and_save_roundtrip(self, plugin:TestHarness) -> None:
        from explorer.ui import prefs as prefs_ui
        from explorer.constants import CFG_SCAN_VALUE_THRESHOLD, CFG_OVERLAY_ENABLED

        frame = prefs_ui.build_prefs(plugin.parent, "Testy", False)
        assert frame is not None

        prefs_ui._pref_vars[CFG_SCAN_VALUE_THRESHOLD].set("123456")
        prefs_ui._pref_vars[CFG_OVERLAY_ENABLED].set(False)
        prefs_ui.save_prefs("Testy", False)

        assert plugin.config.get_int(CFG_SCAN_VALUE_THRESHOLD) == 123456
        assert plugin.config.get_bool(CFG_OVERLAY_ENABLED) is False

    def test_invalid_threshold_falls_back_to_default(self, plugin:TestHarness) -> None:
        from explorer.ui import prefs as prefs_ui
        from explorer.constants import CFG_EXOBIO_VALUE_THRESHOLD, DEFAULT_EXOBIO_VALUE_THRESHOLD

        prefs_ui.build_prefs(plugin.parent, "Testy", False)
        prefs_ui._pref_vars[CFG_EXOBIO_VALUE_THRESHOLD].set("not-a-number")
        prefs_ui.save_prefs("Testy", False)

        assert plugin.config.get_int(CFG_EXOBIO_VALUE_THRESHOLD) == DEFAULT_EXOBIO_VALUE_THRESHOLD

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
