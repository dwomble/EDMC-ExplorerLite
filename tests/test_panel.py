"""
Unit tests for the compact panel (explorer/ui/panel.py) and prefs (explorer/ui/prefs.py).

Run with:
    .venv/bin/python -m pytest tests/test_panel.py -v --tb=short

`harness` (session-scoped, one shared Tk root for the whole test run) comes from
conftest.py -- see its docstring for why.
"""
import tkinter as tk
import pytest
from typing import Generator

from harness import TestHarness, reset_plugin_modules
from explorer.ui.panel import _credits_range

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
    """
    Flatten the panel's children into one string per visual "line", for substring assertions.
    Plain rows are a single th.Label with a "text" option; a gridded table (see panel.py's
    _render_table) is a Frame whose grid children get grouped by row and space-joined back into
    an equivalent line, so callers don't need to know whether a given row is columnar or not.
    """
    lines:list[str] = []
    for child in load.panel.scroll.interior.winfo_children():
        if isinstance(child, tk.Frame):
            rows:dict[int, dict[int, str]] = {}
            for cell in child.winfo_children():
                info = cell.grid_info()
                rows.setdefault(int(info["row"]), {})[int(info["column"])] = cell["text"]
            for row_index in sorted(rows):
                cells = rows[row_index]
                lines.append(" ".join(cells[c] for c in sorted(cells)))
        else:
            lines.append(child["text"])
    return lines

class TestCreditsRange:

    def test_shared_unit_suffix_is_shown_once(self) -> None:
        assert _credits_range(12_200_000, 16_300_000) == "12.2-16.3M Cr"

    def test_mismatched_unit_suffix_shows_both_in_full(self) -> None:
        assert _credits_range(500_000, 16_300_000) == "500K Cr-16.3M Cr"

    def test_collapses_to_a_single_value_when_min_equals_max(self) -> None:
        assert _credits_range(1_000_000, 1_000_000) == "1M Cr"

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
        assert lines[0] == "QuietSpace — 1 bodies, 0 signals — done"

    def test_full_walkthrough_shows_flagged_bodies_section(self, plugin:TestHarness) -> None:
        plugin.config.set("EDMCExplorerLite_ScanValueThreshold", 50000)
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        import load
        lines = _panel_lines(load)
        assert lines[0].startswith("Deltius —")
        assert any(line.startswith("A 1 ") for line in lines)

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
        assert any(" — done" in line or " — scan needed" in line for line in lines)
        assert any(line.startswith("A 1 ") for line in lines)

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
        assert any("Bacterium Aurasus 2/3 1M Cr" in line for line in lines)

        for event in events[cutoff:]:
            plugin.fire_event(event)

        lines = _panel_lines(load)
        # Both the flagged-list line and the on-body detail table should vanish once the
        # genus is fully sampled -- not just one or the other.
        assert not any("Bacterium" in line for line in lines)

    def test_confirmed_unsampled_genus_lists_possible_species(self, plugin:TestHarness) -> None:
        """
        A genus confirmed via SAASignalsFound but not yet sampled used to show a generic
        "Bacterium sp." placeholder -- not useful, since we already have a Scan-time
        prediction (still sitting in genus_predictions) narrowing which species it's likely
        to be. Should list those instead, genus once + species epithets joined by "/".
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [
            ("Bacterium", "Bacterium Acies", 0.9),
            ("Bacterium", "Bacterium Aurasus", 0.8),
        ])

        assert load.panel._possible_species_label(body_pk, "Bacterium") == "Bacterium Acies/Aurasus"

    def test_possible_species_label_falls_back_without_any_prediction(self, plugin:TestHarness) -> None:
        """ A genus with no species-level prediction data (or none matching this body) falls
        back to the old generic placeholder rather than an empty label. """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")

        assert load.panel._possible_species_label(body_pk, "Anemone") == "Anemone sp."

    def test_possible_species_label_truncates_when_too_long(self, plugin:TestHarness) -> None:
        """ Many tied candidates should truncate rather than run the row on indefinitely. """
        from explorer.state import state as explorer_state
        from explorer.ui.panel import MAX_SPECIES_LABEL_CHARS

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [
            ("Bacterium", "Bacterium Acies", 0.99),
            ("Bacterium", "Bacterium Alcyoneum", 0.98),
            ("Bacterium", "Bacterium Aurasus", 0.97),
            ("Bacterium", "Bacterium Bullaris", 0.96),
            ("Bacterium", "Bacterium Cerbrus", 0.95),
        ])

        label:str = load.panel._possible_species_label(body_pk, "Bacterium")
        assert len(label) <= MAX_SPECIES_LABEL_CHARS
        assert label.startswith("Bacterium Acies"), label # best-confidence candidate survives truncation

    def test_predicted_genus_line_is_superseded_by_confirmed_genus(self, plugin:TestHarness) -> None:
        """
        Regression test for the pre-DSS genus predictor: a landable body whose Scan properties
        match known genera's conditions should show a "N species ..." line (unconfirmed) in the
        flagged-body list before any DSS data exists -- the species count itself isn't in doubt,
        only which genus it is, so no "?" on the count -- and once SAASignalsFound later
        confirms what's there, the tag should name the actual genus, not a bare count (and the
        body should stay listed, not read as "nothing flagged").
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
        # flagged", printing that line right above the predicted body below it.
        assert not any("Nothing flagged" in line for line in lines), lines

        plugin.fire_event(events[confirm_index])

        lines = _panel_lines(load)
        assert any(line.startswith("A 1 ") and "Bacterium" in line for line in lines), lines
        assert not any(line.startswith("A 1 ") and "1 species" in line for line in lines), lines

    def test_unconfirmed_genus_guess_shows_a_value_range_not_a_single_number(self, plugin:TestHarness) -> None:
        """
        Regression test: a genus-only guess (no species-level narrowing available for that
        genus, e.g. Anemone -- see species_conditions.py's scope) used to show just the top of
        that genus's value range as a single "estimated" number, reading as more precise than
        it really is -- the actual species present could be worth far less. Should show the
        full min-max range instead.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [("Anemone", None, 0.9)])

        best:list[dict] = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 1, best
        assert best[0]["value_min"] < best[0]["value_max"], "test premise: Anemone should have a real min-max spread"

        rendered:tuple[str, str, str] = load.panel._predicted_genus_row(best[0])
        assert "-" in rendered[2], rendered # e.g. "~1.5-3.4M Cr", not a single number

    def test_scan_narrows_prediction_to_species_when_data_available(self, plugin:TestHarness) -> None:
        """
        Regression/coverage for species-level narrowing (valuation/species_conditions.py): a
        Scan matching a specific species' own spawn conditions -- not just its genus's wider
        range -- should store that species name and its exact confirmed value, not just a
        generic genus guess. Checked at the store level (not the panel's capped top-3 display)
        since a body can plausibly match several genera/species at once and we only care that
        this one specific species is *among* what got stored, not that it's the only one.
        """
        from explorer.state import state as explorer_state

        plugin.config.set("EDMCExplorerLite_ExobioValueThreshold", 500_000) # Tussock Ignis is 1.85M Cr, below the 5M default
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("species_level_prediction", 0.02)

        import load
        assert explorer_state.system_id is not None
        flagged = load.store.get_flagged_bodies_for_system(explorer_state.system_id)
        body = next(b for b in flagged if b["body_name"] == "Speciesia A 1")
        predictions = load.store.get_genus_predictions_for_body(body["id"])
        assert any(
            p["genus"] == "Tussock" and p["species"] == "Tussock Ignis" and p["confidence"] >= 0.99
            for p in predictions
        ), [dict(p) for p in predictions]

    def test_predicted_value_does_not_double_count_same_genus_species_guesses(self, plugin:TestHarness) -> None:
        """
        Regression test for _best_predictions_for_body(): a body can have several candidate
        SPECIES stored within the SAME genus (alternative guesses at one real signal, not
        separate ones -- see genus_prediction.predict_species()). The flagged-list/on-body total
        must count that genus once, via its best-confidence candidate, not every guess -- and
        the overall list should cap to the body's real biological_signal_count once known,
        rather than an arbitrary top-3.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, biological_signal_count=2, has_biological_signals=1)
        load.store.replace_genus_predictions(body_pk, [
            ("Tussock", "Tussock Ignis", 0.95),
            ("Tussock", "Tussock Pennata", 0.80),
            ("Bacterium", "Bacterium Aurasus", 0.90),
        ])

        best = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 2, best # capped to the body's known biological_signal_count
        names = [slot["name"] for slot in best]
        assert "Tussock Ignis" in names, best # kept the higher-confidence Tussock candidate
        assert "Tussock Pennata" not in names, best

    def test_signal_count_bias_prefers_chain_expected_genus_over_raw_confidence(self, plugin:TestHarness) -> None:
        """
        Regression/coverage for the signal-count chain bias (valuation/signal_count_bias.py): on
        a lone (count=1) signal, Bacterium is the "usually" expected genus even when a different,
        unrelated genus scored higher confidence from Scan conditions alone -- the chain is a
        tiebreak among already-eligible candidates, so it should still win that one slot.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, biological_signal_count=1, atmosphere_type="CarbonDioxide", planet_class="Rocky body")
        load.store.replace_genus_predictions(body_pk, [
            ("Frutexa", "Frutexa Acus", 0.99), # highest raw confidence, but not the tier-1 expected genus
            ("Bacterium", "Bacterium Aurasus", 0.50),
        ])

        best = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 1, best
        assert best[0]["name"] == "Bacterium Aurasus", best

    def test_signal_count_bias_disabled_on_exception_atmospheres(self, plugin:TestHarness) -> None:
        """ Thin Water/Oxygen/Nitrogen bodies don't follow the chain at all (direct field
        report) -- selection should fall back to plain confidence ordering there. """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, biological_signal_count=1, atmosphere_type="Water", planet_class="Rocky body")
        load.store.replace_genus_predictions(body_pk, [
            ("Frutexa", "Frutexa Acus", 0.99),
            ("Bacterium", "Bacterium Aurasus", 0.50),
        ])

        best = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 1, best
        assert best[0]["name"] == "Frutexa Acus", best # highest confidence wins -- no chain bias here

    def test_tied_genera_are_merged_not_silently_resolved_by_chain_bias(self, plugin:TestHarness) -> None:
        """
        Regression test from a real journal case: an HMC single-signal body scored Bacterium
        and Stratum Tectonicas EQUALLY on physics-based confidence. The old tier-1 chain bias
        picked Stratum outright (a ~19M Cr guess) when the confirmed answer was Bacterium
        (~1.7M Cr) -- genuinely tied candidates must merge into one slot spanning both
        possibilities, not let the chain silently choose between them.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, biological_signal_count=1, atmosphere_type="SulphurDioxide", planet_class="High metal content body")
        load.store.replace_genus_predictions(body_pk, [
            ("Bacterium", "Bacterium Cerbrus", 1.0),
            ("Stratum", "Stratum Tectonicas", 1.0),
        ])

        best = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 1, best # still exactly one real signal
        assert "Bacterium Cerbrus" in best[0]["name"], best
        assert "Stratum Tectonicas" in best[0]["name"], best
        assert best[0]["value_min"] < best[0]["value_max"], best # spans both possibilities

    def test_tied_genera_get_separate_slots_when_there_is_room_for_both(self, plugin:TestHarness) -> None:
        """
        Regression test from a real journal case: a body with biological_signal_count=2 had
        Frutexa and Recepta both scoring confidence 1.0. The tie-merge fix above used to merge
        ANY tie into one slot regardless of how many slots were actually available, collapsing
        this 2-signal body down to a single displayed "Frutexa or Recepta" guess. A tie should
        only merge when it doesn't fit in the remaining slots -- here there's room for both.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, biological_signal_count=2, atmosphere_type="CarbonDioxide", planet_class="Rocky body")
        load.store.replace_genus_predictions(body_pk, [
            ("Frutexa", "Frutexa Acus", 1.0),
            ("Recepta", "Recepta Conditivus", 1.0),
            ("Tubus", "Tubus Cavas", 0.29),
        ])

        best = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 2, best # two real signals -- Frutexa and Recepta each get their own slot
        names = [slot["name"] for slot in best]
        assert names == ["Frutexa Acus", "Recepta Conditivus"], best # not merged, Tubus dropped (lower confidence)

    def test_known_bio_signals_count_even_without_dss_or_prediction(self, plugin:TestHarness) -> None:
        """
        Regression test: FSSBodySignals can confirm a body has biological signals well before
        it's DSS'd (SAASignalsFound) or even Scanned (so no genus_prediction guess exists yet
        either). Those bodies used to vanish from the flagged list entirely -- only the one
        body actually DSS'd in the system showed up at all -- even though we already know for
        certain that other bodies in the system have biology too.
        """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("known_bio_signals_before_dss", 0.02)

        import load
        lines = _panel_lines(load)
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
        # The on-body detail table (not just the flagged-list "N species" line) should be
        # showing -- its confidence percentage is the distinguishing marker between the two.
        assert any("%)" in line for line in lines), lines
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
