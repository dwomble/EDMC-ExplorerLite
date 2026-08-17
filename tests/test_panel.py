"""
Unit tests for the compact panel (explorer/ui/panel.py) and prefs (explorer/ui/prefs.py).

Run with:
    .venv/bin/python -m pytest tests/test_panel.py -v --tb=short

`harness` (session-scoped, one shared Tk root for the whole test run) comes from
conftest.py -- see its docstring for why.
"""
import tkinter as tk
import sqlite3
import pytest
from typing import Generator, cast

from harness import TestHarness, reset_plugin_modules
from explorer.db.store import ExplorerStore
from explorer.ui.panel import _credits_range, system_status_text, system_header_line, system_body_count_text

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

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

def _panel_lines(load) -> list[str]:
    """
    Flatten the panel's children into one string per visual "line", for substring assertions.
    Plain rows are a single th.Label with a "text" option; a gridded table (see panel.py's
    _render_table) is a Frame whose grid children get grouped by row and space-joined back into
    an equivalent line, so callers don't need to know whether a given row is columnar or not.
    """
    lines:list[str] = []
    # sorted by grid row, not creation order -- a widget rebuilt out of sync with its siblings
    # (e.g. the header changing while a body row stays put) otherwise lands at the wrong index
    children:list[tk.Widget] = sorted(load.panel.scroll.interior.winfo_children(), key=lambda c: int(c.grid_info()["row"]))
    for child in children:
        if isinstance(child, tk.Frame):
            rows:dict[int, dict[int, str]] = {}
            for cell in child.winfo_children():
                widget:tk.Widget = cast(tk.Widget, cell) # always a Label here, never a Toplevel
                info = widget.grid_info()
                rows.setdefault(int(info["row"]), {})[int(info["column"])] = widget["text"]
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

class TestSystemStatusText:
    """ Honk -> FSS -> DSS/Sample/"DSS + Sample" -> Done. Needs a real store now (checking
    per-body DSS/sample status), not just a dict standing in for a sqlite3.Row. """

    def test_before_honking(self, store:ExplorerStore) -> None:
        cmdr_id = store.get_or_create_cmdr("Testy")
        system_id = store.get_or_create_system(cmdr_id, 1, "Deltius")
        assert system_status_text(store, store.get_system(system_id)) == "Honk"

    def test_quiet_system_is_done_even_mid_fss(self, store:ExplorerStore) -> None:
        cmdr_id = store.get_or_create_cmdr("Testy")
        system_id = store.get_or_create_system(cmdr_id, 1, "Deltius")
        store.update_system(system_id, honk_body_count=1, honk_hint="probably quiet", all_bodies_found=0)
        assert system_status_text(store, store.get_system(system_id)) == "Done"

    def test_fss_shown_until_all_bodies_found(self, store:ExplorerStore) -> None:
        """ FSS stays shown for the whole pass, even once a body is already flagged -- FSS
        must finish before DSS/Sample/Done are even considered. """
        cmdr_id = store.get_or_create_cmdr("Testy")
        system_id = store.get_or_create_system(cmdr_id, 1, "Deltius")
        store.update_system(system_id, honk_body_count=7, honk_hint="worth a full scan", all_bodies_found=0)
        body_pk = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius A 1", "Planet")
        store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000)
        assert system_status_text(store, store.get_system(system_id)) == "FSS"

    def test_dss_once_fss_completes_with_an_unmapped_flagged_body(self, store:ExplorerStore) -> None:
        cmdr_id = store.get_or_create_cmdr("Testy")
        system_id = store.get_or_create_system(cmdr_id, 1, "Deltius")
        store.update_system(system_id, honk_body_count=1, honk_hint="worth a full scan", all_bodies_found=1)
        body_pk = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius A 1", "Planet")
        store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000)
        assert system_status_text(store, store.get_system(system_id)) == "DSS"

    def test_sample_once_mapped_with_active_species(self, store:ExplorerStore) -> None:
        cmdr_id = store.get_or_create_cmdr("Testy")
        system_id = store.get_or_create_system(cmdr_id, 1, "Deltius")
        store.update_system(system_id, honk_body_count=1, honk_hint="worth a full scan", all_bodies_found=1)
        body_pk = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius A 1", "Planet")
        store.update_body(body_pk, has_biological_signals=1, mapped_at="2026-08-17T00:00:00Z")
        store.get_or_create_species_progress(body_pk, "Bacterium")
        assert system_status_text(store, store.get_system(system_id)) == "Sample"

    def test_dss_and_sample_combine(self, store:ExplorerStore) -> None:
        cmdr_id = store.get_or_create_cmdr("Testy")
        system_id = store.get_or_create_system(cmdr_id, 1, "Deltius")
        store.update_system(system_id, honk_body_count=2, honk_hint="worth a full scan", all_bodies_found=1)
        unmapped_pk = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius A 1", "Planet")
        store.update_body(unmapped_pk, flagged_value=1, estimated_scan_value=1_000_000)
        mapped_pk = store.get_or_create_body(cmdr_id, system_id, 2, "Deltius A 2", "Planet")
        store.update_body(mapped_pk, has_biological_signals=1, mapped_at="2026-08-17T00:00:00Z")
        store.get_or_create_species_progress(mapped_pk, "Bacterium")
        assert system_status_text(store, store.get_system(system_id)) == "DSS + Sample"

    def test_done_once_fully_sampled_and_mapped(self, store:ExplorerStore) -> None:
        cmdr_id = store.get_or_create_cmdr("Testy")
        system_id = store.get_or_create_system(cmdr_id, 1, "Deltius")
        store.update_system(system_id, honk_body_count=1, honk_hint="worth a full scan", all_bodies_found=1)
        body_pk = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius A 1", "Planet")
        store.update_body(body_pk, has_biological_signals=1, mapped_at="2026-08-17T00:00:00Z")
        progress_id = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(progress_id, completed_at="2026-08-17T00:00:00Z")
        assert system_status_text(store, store.get_system(system_id)) == "Done"

    def test_header_line_prepends_the_system_name(self, store:ExplorerStore) -> None:
        cmdr_id = store.get_or_create_cmdr("Testy")
        system_id = store.get_or_create_system(cmdr_id, 1, "Deltius")
        store.update_system(system_id, honk_body_count=7, honk_hint="worth a full scan", all_bodies_found=0)
        assert system_header_line(store, store.get_system(system_id)) == "Deltius — 7 bodies — FSS"

    def test_body_count_text_is_the_known_count_not_fss_progress(self, store:ExplorerStore) -> None:
        cmdr_id = store.get_or_create_cmdr("Testy")
        system_id = store.get_or_create_system(cmdr_id, 1, "Deltius")
        assert system_body_count_text(store.get_system(system_id)) == "" # not honked yet

        store.update_system(system_id, honk_body_count=1)
        assert system_body_count_text(store.get_system(system_id)) == "1 body"

        store.update_system(system_id, honk_body_count=7)
        assert system_body_count_text(store.get_system(system_id)) == "7 bodies"

class TestPanelStates:

    def test_idle_state_is_a_single_line(self, plugin:TestHarness) -> None:
        import load
        assert load.store is not None and load.panel is not None
        lines = _panel_lines(load)
        assert lines == ["Explorer — idle"]

    def test_refresh_does_not_rebuild_widgets_when_content_is_unchanged(self, plugin:TestHarness) -> None:
        """
        Real-world regression: refresh() used to destroy and recreate every Label/Frame on
        every single call, even when the new content was identical to what was already
        showing -- a visible flicker on essentially any journal/dashboard event (landing,
        flying, scanning...), not just ones that actually changed the display. refresh()
        should leave the existing widgets alone when nothing actually changed.
        """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.panel is not None
        before = list(load.panel.scroll.interior.winfo_children())
        assert before # sanity check: something is actually showing

        load.panel.refresh() # same state, nothing changed

        after = list(load.panel.scroll.interior.winfo_children())
        assert before == after # same widget objects, not just equal text -- never destroyed

    def test_refresh_only_rebuilds_the_row_that_changed(self, plugin:TestHarness) -> None:
        """
        A row unrelated to whatever changed shouldn't be touched either -- e.g. scanning a
        sample on one body, or a new flagged body appearing, shouldn't flicker the system
        summary line above it.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        summary_row_before = load.panel.scroll.interior.winfo_children()[0]

        # Add a flagged body -- a new row should appear, but the summary line's own widget
        # (row 0, unrelated to this body) must not be touched.
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000)
        load.panel.refresh()

        rows_after = load.panel.scroll.interior.winfo_children()
        assert len(rows_after) == 2, rows_after
        assert rows_after[0] is summary_row_before # untouched -- same object

    def test_honk_state_shows_counts_and_verdict(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        lines = _panel_lines(load)
        assert lines[0] == "QuietSpace — 1 body — Done"

    def test_full_walkthrough_shows_flagged_bodies_section(self, plugin:TestHarness) -> None:
        plugin.config.set("EDMCExplorerLite_ScanValueThreshold", 50000)
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        import load
        assert load.store is not None and load.panel is not None
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
        assert load.store is not None and load.panel is not None
        lines = _panel_lines(load)
        assert any(line.endswith("FSS") for line in lines)
        assert any(line.startswith("A 1 ") for line in lines)

    def test_flagged_body_order_matches_the_overlay(self, plugin:TestHarness) -> None:
        """
        Real-world report: the panel and overlay listed a system's flagged bodies in different
        orders. The panel used plain body_id order; the overlay already sorted biological
        bodies first (see test_overlay_summary.py's own version of this regression). Both now
        share flagged_body_sort_key(), so a biological body always leads regardless of body_id.
        """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None

        cart_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 1, "QuietSpace 1")
        load.store.update_body(cart_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)
        bio_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 2, "QuietSpace Bio")
        load.store.update_body(bio_pk, has_biological_signals=1, biological_signal_count=3)

        load.panel.refresh()
        lines = _panel_lines(load)
        bio_index:int = next(i for i, line in enumerate(lines) if "Bio" in line)
        cart_index:int = next(i for i, line in enumerate(lines) if line.startswith("1 "))
        assert bio_index < cart_index, lines

    def test_binary_star_system_is_quiet(self, plugin:TestHarness) -> None:
        """ A system with no planets at all (e.g. a bare binary) has nothing to flag -- just the
        top summary line, no extra "nothing found" commentary. """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("binary_star_only_system", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        lines = _panel_lines(load)
        assert lines == ["Starrock — 2 bodies — Done"], lines

    def test_exobio_line_shows_progress_then_drops_once_done(self, plugin:TestHarness) -> None:
        """
        Regression test for the progressive-detail redesign: a flagged body's exobio line
        should read as a generic "genus ~value" guess, become "species, sampling distance,
        value" once sampling starts, and disappear once that genus is fully sampled -- not
        keep showing a stale "exobio~9M Cr" label throughout.
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
        assert load.store is not None and load.panel is not None
        lines = _panel_lines(load)
        # 5M Cr, not 1M -- this fixture's body has no WasFootfalled (unset defaults to "nobody
        # has yet"), so the shown value is Full (base 1M x5 first-logged bonus), not Base.
        assert any("Bacterium Aurasus 2/3 500m 5M Cr" in line for line in lines)

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
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [
            ("Bacterium", "Bacterium Acies", 0.9),
            ("Bacterium", "Bacterium Aurasus", 0.8),
        ])

        assert load.panel._possible_species_label(body_pk, "Bacterium") == "Bacterium Acies/Aurasus"

    def test_confirmed_genus_value_narrows_not_widens(self, plugin:TestHarness) -> None:
        """
        Real-world regression: confirming a genus via SAASignalsFound used to fall back to that
        genus's FULL unnarrowed value range (estimate_genus_range), discarding the Scan-time
        species-level prediction that had already narrowed it down -- so the estimate widened
        after mapping instead of narrowing. Concha's full range is ~2.35-16.78M, but this body's
        conditions only ever matched "Concha Aureolas" (~7.77M exact) -- confirming the genus
        should keep that narrowed range, not fall back to the wider one.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [("Concha", "Concha Aureolas", 1.0)])
        progress_id:int = load.store.get_or_create_species_progress(body_pk, "Concha") # SAASignalsFound: genus confirmed

        row = load.store.get_species_progress_row(progress_id)
        assert row is not None
        value_min, value_max = load.panel._exobio_row_range(row)
        assert (value_min, value_max) == (7_774_700, 7_774_700), (value_min, value_max)

    def test_possible_species_label_falls_back_without_any_prediction(self, plugin:TestHarness) -> None:
        """ A genus with no species-level prediction data (or none matching this body) falls
        back to the old generic placeholder rather than an empty label. """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
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
        assert load.store is not None and load.panel is not None
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
        match known genera's conditions should show a "?<genus/species> ..." guess (unconfirmed,
        marked with "?") in the flagged-body list before any DSS data exists, and once
        SAASignalsFound later confirms what's there, the tag should switch to a scanned/total
        count (see _flagged_body_row) rather than the predicted guess (and the body should
        stay listed, not read as "nothing flagged").
        """
        plugin.load_events("explorer_events.json")
        events = plugin.events["predicted_then_confirmed"]

        confirm_index:int = next(i for i, e in enumerate(events) if e.get("event") == "SAASignalsFound")
        for event in events[:confirm_index]:
            plugin.fire_event(event)

        import load
        assert load.store is not None and load.panel is not None
        lines = _panel_lines(load)
        assert any(line.startswith("A 1 ") and "?" in line for line in lines), lines
        # Regression: a predicted-only (unconfirmed) body used to still count as "nothing
        # flagged", printing that line right above the predicted body below it.
        assert not any("Nothing flagged" in line for line in lines), lines

        plugin.fire_event(events[confirm_index])

        lines = _panel_lines(load)
        assert any(line.startswith("A 1 ") and "0 of 1 scanned" in line for line in lines), lines

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
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [("Anemone", None, 0.9)])

        best:list[dict] = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 1, best
        assert best[0]["value_min"] < best[0]["value_max"], "test premise: Anemone should have a real min-max spread"

        rendered:tuple[str, str, str] = load.panel._predicted_genus_row(best[0], confirmed_signal=False, was_footfalled=True)
        assert "-" in rendered[2], rendered # e.g. "~1.5-3.4M Cr", not a single number
        assert rendered[2].startswith("~"), rendered # genuine range -- "~" is warranted here

    def test_predicted_row_has_no_uncertainty_marker_once_narrowed_to_one_species(self, plugin:TestHarness) -> None:
        """
        Regression: "~" used to be prepended unconditionally for any not-yet-confirmed genus,
        even once Scan-time narrowing had already collapsed the candidates to a single species
        -- species values are fixed, so that number is already exact, not an estimate.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [("Bacterium", "Bacterium Alcyoneum", 1.0)])

        best:list[dict] = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 1, best
        assert best[0]["value_min"] == best[0]["value_max"], "test premise: a single candidate is already exact"

        rendered:tuple[str, str, str] = load.panel._predicted_genus_row(best[0], confirmed_signal=False, was_footfalled=True)
        assert not rendered[2].startswith("~"), rendered

    def test_confirmed_genus_row_has_no_uncertainty_marker_once_narrowed_to_one_species(self, plugin:TestHarness) -> None:
        """ Same fix, on the on-body detail row (_exobio_progress_row): a genus confirmed via
        SAASignalsFound but not yet sampled, narrowed to one surviving candidate species, is
        already an exact value -- not an estimate. """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [("Bacterium", "Bacterium Alcyoneum", 1.0)])
        progress_id:int = load.store.get_or_create_species_progress(body_pk, "Bacterium")

        row:sqlite3.Row|None = load.store.get_species_progress_row(progress_id)
        assert row is not None
        rendered:tuple[str, str, str, str] = load.panel._exobio_progress_row(row, was_footfalled=True)
        assert not rendered[3].startswith("~"), rendered

        # Contrast: still-tied candidates with DIFFERENT values keep the marker.
        load.store.replace_genus_predictions(body_pk, [
            ("Bacterium", "Bacterium Cerbrus", 1.0),
            ("Bacterium", "Bacterium Tela", 1.0),
        ])
        rendered = load.panel._exobio_progress_row(row, was_footfalled=True)
        assert rendered[3].startswith("~"), rendered

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
        assert load.store is not None and load.panel is not None
        assert explorer_state.system_id is not None
        flagged = load.store.get_flagged_bodies_for_system(explorer_state.system_id)
        body = next(b for b in flagged if b["body_name"] == "Speciesia A 1")
        predictions = load.store.get_genus_predictions_for_body(body["id"])
        assert any(
            p["genus"] == "Tussock" and p["species"] == "Tussock Ignis" and p["confidence"] >= 0.99
            for p in predictions
        ), [dict(p) for p in predictions]

    def test_confirmed_biological_signal_still_shows_a_guess_below_value_threshold(self, plugin:TestHarness) -> None:
        """
        Real-world regression: FSSBodySignals confirmed a biological signal exists (ground
        truth) BEFORE the body's own Scan (Detailed) arrived -- the common order when a full FSS
        sweep of the system happens before flying to each body. This body's conditions are
        generic enough that 8 genera tie at top confidence (a real, common occurrence -- hard
        categorical gates alone decide eligibility for most rulesets), so the shown guess is a
        "N possible genera" summary rather than any one species name -- but it must still show
        SOMETHING, not silently vanish into a bare "biological signal" line just because the
        underlying species-level values happen to be low.
        """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("confirmed_biology_below_threshold", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        lines = _panel_lines(load)
        assert any(line.startswith("A 1 ") and "possible genera" in line for line in lines), lines
        assert not any("biological signal" in line for line in lines), lines

    def test_many_tied_genera_collapse_to_count(self, plugin:TestHarness) -> None:
        """
        Real-world regression: a body with several signals and many genera tied at the same
        confidence used to render every one of them "A or B or C..." on one line, badly
        overflowing the panel's width (a real ~180-character line was reported in play).
        Collapsing to a short count keeps the row readable; the individual names are still
        knowable on-body once SAASignalsFound narrows it down.
        """
        from explorer.state import state as explorer_state

        plugin.config.set("EDMCExplorerLite_ScanValueThreshold", 50000)
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("confirmed_biology_below_threshold", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.system_id is not None
        flagged = load.store.get_flagged_bodies_for_system(explorer_state.system_id)
        body = next(b for b in flagged if b["body_name"] == "Speciesia A 1")
        best = load.panel._best_predictions_for_body(body["id"])
        assert len(best) == 1, best # only 1 real signal -- everything tied collapses to 1 slot
        assert best[0]["name"] == "8 possible genera", best

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
        assert load.store is not None and load.panel is not None
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

    def test_tied_species_widen_value_range(self, plugin:TestHarness) -> None:
        """
        Real-world regression: on a real body, Frutexa Flabellum and Frutexa Flammasis both
        tied at confidence 1.0 (Frutexa's own rulesets don't distinguish them for these
        conditions), but Flammasis (~10.3M Cr) is worth far more than Flabellum (~1.8M Cr).
        Picking just one as "the" representative and computing its value alone silently
        understated the true range -- both tied alternates must widen value_min/value_max,
        even though only one name is shown.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [
            ("Frutexa", "Frutexa Flabellum", 1.0),
            ("Frutexa", "Frutexa Flammasis", 1.0),
        ])

        best = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 1, best
        assert best[0]["value_max"] >= 10_000_000, best # must reflect Flammasis, not just the shown Flabellum

    def test_chain_tiers_get_own_slots(self, plugin:TestHarness) -> None:
        """
        Real-world regression: a 7-signal body had 9 genera all tie at confidence 1.0 (common --
        most rulesets only use hard categorical gates, no numeric axis to break a tie). With 7
        slots available, collapsing straight to "9 possible genera" throws away information we
        actually have: the chain's priority order (Bacterium/Stratum/Tussock/Osseus-or-Tubus/
        Concha-or-Frutexa) still applies even past signal count 5 -- tiers 1-5 remain expected,
        the extra 2 signals are just unclassified. Each matching tier should get its own
        individual slot; only the genuine excess (non-chain genera beyond the slot budget)
        collapses into one merged slot.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, biological_signal_count=7, atmosphere_type="Ammonia", planet_class="Rocky body")
        load.store.replace_genus_predictions(body_pk, [
            (genus, f"{genus} X", 1.0) for genus in
            ["Aleoida", "Bacterium", "Cactoida", "Concha", "Frutexa", "Fungoida", "Osseus", "Stratum", "Tussock"]
        ])

        best = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 7, best # capped to the real signal count
        names = [slot["name"] for slot in best]
        for chain_genus in ("Bacterium X", "Stratum X", "Tussock X", "Osseus X"):
            assert chain_genus in names, best # each chain tier got its own dedicated slot
        assert any("Concha X" in n and "Frutexa X" in n for n in names), best # tier 5's own pair, merged as one slot
        assert not any("possible genera" in n for n in names), best # room enough that nothing needed to collapse to a count

    def test_flagged_row_genus_count_is_distinct_genera_not_slot_count(self, plugin:TestHarness) -> None:
        """
        An 8-signal body with Osseus-or-Tubus and Concha-or-Frutexa each tied for their own tier
        has 10 distinct possible genus names spread across 8 real signal slots. "10 possible
        genera" is the right label -- it tells the player 10 different kinds of organism could
        turn up here, even though only 8 of them actually will. The summed value alongside it
        still only adds up 8 slots (one per real signal); the two numbers describe different
        things and aren't meant to match.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(
            body_pk, has_biological_signals=1, biological_signal_count=8, atmosphere_type="Ammonia", planet_class="Rocky body"
        )
        load.store.replace_genus_predictions(body_pk, [
            (genus, f"{genus} X", 1.0) for genus in
            ["Aleoida", "Bacterium", "Cactoida", "Concha", "Frutexa", "Fungoida", "Osseus", "Tubus", "Stratum", "Tussock"]
        ])

        body:sqlite3.Row|None = load.store.get_body(body_pk)
        assert body is not None
        row = load.panel._flagged_body_row("QuietSpace", body)
        assert row is not None
        assert row[4] == "8 of 10 possible genera", row

    def test_confirmed_zero_signals_suppresses_a_stale_prediction(self, plugin:TestHarness) -> None:
        """
        Real-world report: a Terraformable HMC still showed a "?3 genera" guess even though
        FSSBodySignals had already confirmed zero biological signals. genus_predictions rows
        are written at Scan time from planetary conditions alone, unaware of what
        FSSBodySignals later confirms (or already confirmed) -- a stale guess must never
        override a confirmed zero.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, has_biological_signals=0, biological_signal_count=0)
        load.store.replace_genus_predictions(body_pk, [("Bacterium", "Bacterium X", 1.0)])

        assert load.panel._best_predictions_for_body(body_pk) == []

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
        assert load.store is not None and load.panel is not None
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
        assert load.store is not None and load.panel is not None
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
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, biological_signal_count=1, atmosphere_type="SulphurDioxide", planet_class="High metal content body")
        load.store.replace_genus_predictions(body_pk, [
            ("Bacterium", "Bacterium Cerbrus", 1.0),
            ("Stratum", "Stratum Tectonicas", 1.0),
        ])

        best = load.panel._best_predictions_for_body(body_pk)
        assert len(best) == 1, best # still exactly one real signal
        assert "Bac. Cerbrus" in best[0]["name"], best # abbreviated -- both tied names, neither dropped
        assert "Str. Tectonicas" in best[0]["name"], best
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
        assert load.store is not None and load.panel is not None
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
        assert load.store is not None and load.panel is not None
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
        assert load.store is not None and load.panel is not None
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
        assert load.store is not None and load.panel is not None
        lines = _panel_lines(load)
        assert any(line.startswith("A 1 (MR) ") for line in lines), lines

    def test_flagged_row_shows_gravity(self, plugin:TestHarness) -> None:
        """ Gravity is stored raw (m/s^2, matching the journal) and shown converted to G. """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, surface_gravity=9.797759 * 1.5)

        body:sqlite3.Row|None = load.store.get_body(body_pk)
        assert body is not None
        row = load.panel._flagged_body_row("QuietSpace", body)
        assert row is not None
        assert row[2] == "1.50g", row

    def test_flagged_row_shows_unknown_gravity(self, plugin:TestHarness) -> None:
        """ No Scan (Detailed) yet -- gravity is unknown, not a bogus zero. """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, has_biological_signals=1, biological_signal_count=1)

        body:sqlite3.Row|None = load.store.get_body(body_pk)
        assert body is not None
        row = load.panel._flagged_body_row("QuietSpace", body)
        assert row is not None
        assert row[2] == "?g", row

    def test_flagged_row_shows_scanned_count_once_genus_confirmed(self, plugin:TestHarness) -> None:
        """
        A confirmed-but-unsampled genus used to show its species-level narrowing (e.g.
        "Cerbrus/Tela") directly in the flagged row -- replaced by a compact scanned/total
        count (see _flagged_body_row): a full name list became illegible once several genera
        were confirmed on the same body at once. The species-level guess itself still shows in
        full on-body (_exobio_progress_row/_possible_species_label), just not in this summary.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [
            ("Bacterium", "Bacterium Cerbrus", 1.0),
            ("Bacterium", "Bacterium Tela", 1.0),
        ])
        load.store.get_or_create_species_progress(body_pk, "Bacterium") # SAASignalsFound: genus confirmed, not yet sampled

        body:sqlite3.Row|None = load.store.get_body(body_pk)
        assert body is not None
        row = load.panel._flagged_body_row("QuietSpace", body)
        assert row is not None
        assert row[4] == "0 of 1 scanned", row

    def test_flagged_row_shows_scanned_count_while_actively_sampling(self, plugin:TestHarness) -> None:
        """
        Real-world regression: a body with has_biological_signals=1 (its ground-truth signal
        count is always set once FSSBodySignals fires, and never clears) whose genus is
        already confirmed and partway through sampling used to show the raw "N biological
        signals" fallback instead of the "X of Y scanned" progress -- the fallback's condition
        only checked `not predictions`, but predictions is also [] whenever sampling is already
        active, so it clobbered the progress text that had just been set moments earlier.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, has_biological_signals=1, biological_signal_count=7, flagged_exobio=1)
        progress_id:int = load.store.get_or_create_species_progress(body_pk, "Bacterium")
        load.store.update_species_progress(progress_id, species="Bacterium Aurasus", samples_taken=2)

        body:sqlite3.Row|None = load.store.get_body(body_pk)
        assert body is not None
        row = load.panel._flagged_body_row("QuietSpace", body)
        assert row is not None
        assert row[4] == "0 of 1 scanned", row
        assert "biological signal" not in row[4], row

    def test_flagged_row_drops_off_once_every_confirmed_genus_is_fully_sampled(self, plugin:TestHarness) -> None:
        """
        Real-world regression: once every confirmed genus on a body is fully sampled, the row
        used to fall through to the raw FSSBodySignals count ("8 biological signals", "? Cr")
        instead of dropping off -- has_biological_signals stays 1 forever, and that fallback
        didn't check whether the confirmed genus(es) were already done.
        """
        from explorer.state import state as explorer_state
        from explorer.util import now_iso

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, has_biological_signals=1, biological_signal_count=8, flagged_exobio=1)
        progress_id:int = load.store.get_or_create_species_progress(body_pk, "Bacterium")
        load.store.update_species_progress(progress_id, species="Bacterium Aurasus", completed_at=now_iso())

        body:sqlite3.Row|None = load.store.get_body(body_pk)
        assert body is not None
        assert load.panel._flagged_body_row("QuietSpace", body) is None

    def test_current_body_detail_nests_under_its_own_row_not_the_last_flagged_row(self, plugin:TestHarness) -> None:
        """
        Real-world regression: the current-body detail used to render after the WHOLE flagged
        table, so when the current body wasn't the last one listed (sorted by body_id), its
        species list visually read as belonging to whichever body happened to sort last. It
        must nest directly under its own row instead, regardless of table order.
        """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None

        body1_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        body2_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 2, "QuietSpace A 2")
        load.store.update_body(body1_pk, has_biological_signals=1, biological_signal_count=1)
        load.store.update_body(body2_pk, has_biological_signals=1, biological_signal_count=1)
        load.store.replace_genus_predictions(body2_pk, [("Bacterium", None, 0.8)]) # body 2's own flagged guess

        progress_id:int = load.store.get_or_create_species_progress(body1_pk, "Tussock")
        load.store.update_species_progress(progress_id, species="Tussock Ignis", samples_taken=1)

        explorer_state.body_id = 1
        explorer_state.body_name = "QuietSpace A 1"
        load.panel.refresh()

        lines = _panel_lines(load)
        row1_index:int = next(i for i, line in enumerate(lines) if line.startswith("A 1 "))
        row2_index:int = next(i for i, line in enumerate(lines) if line.startswith("A 2 "))
        detail_index:int = next(i for i, line in enumerate(lines) if "Tussock Ignis" in line and "1/3" in line)

        assert row1_index < detail_index < row2_index, lines

    def test_confirmed_signal_drops_prefix(self, plugin:TestHarness) -> None:
        """ The "?" marks a purely speculative guess; it shouldn't apply once a real signal is confirmed. """
        from explorer.state import state as explorer_state

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.replace_genus_predictions(body_pk, [("Anemone", None, 0.9)])

        unconfirmed:sqlite3.Row|None = load.store.get_body(body_pk)
        assert unconfirmed is not None
        row = load.panel._flagged_body_row("QuietSpace", unconfirmed)
        assert row is not None and row[4].startswith("?"), row

        load.store.update_body(body_pk, has_biological_signals=1, biological_signal_count=1)
        confirmed:sqlite3.Row|None = load.store.get_body(body_pk)
        assert confirmed is not None
        row = load.panel._flagged_body_row("QuietSpace", confirmed)
        assert row is not None and not row[4].startswith("?"), row

    def test_supercruise_exit_shows_exobiology_before_landing(self, plugin:TestHarness) -> None:
        """
        Dropping out of supercruise near a body should surface its predicted biology right
        away -- well before ApproachBody/Touchdown/on-foot -- so it's useful for deciding
        whether to land at all.
        """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("supercruise_exit_shows_bio_before_landing", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        lines = _panel_lines(load)
        # The on-body detail table (not just the flagged-list guess line) should be showing,
        # nested directly under the flagged row -- no separate header repeating the body name.
        flagged_index:int = next(i for i, line in enumerate(lines) if line.startswith("A 1 (Icy) "))
        assert lines[flagged_index + 1].startswith("?"), lines # the detail row right below it

class TestNoDuplicateWidgets:
    """
    Regression test for a real bug: th.Base widgets (Button, Checkbutton, ...) only dedupe
    their light/dark pair in the overridden .grid() -- .pack() falls through to the generic
    proxy, which calls pack() on BOTH widgets, rendering the "History" button twice.
    """

    def test_history_button_is_gridded_not_packed(self, plugin:TestHarness) -> None:
        import load
        assert load.store is not None and load.panel is not None
        managers = {load.panel.history_button.obj.winfo_manager(), load.panel.history_button.alt.winfo_manager()}
        assert managers == {"grid", ""} # exactly one of the light/dark pair is actually placed

    def test_toggle_button_is_gridded_not_packed(self, plugin:TestHarness) -> None:
        import load
        assert load.store is not None and load.panel is not None
        managers = {load.panel.toggle_button.obj.winfo_manager(), load.panel.toggle_button.alt.winfo_manager()}
        assert managers == {"grid", ""}

class TestPanelHeaderToggle:
    """ The always-visible header (name + credit totals + History/toggle buttons) and the
    show/hide toggle for everything below it -- collection continues regardless of state. """

    def test_header_shows_plugin_name(self, plugin:TestHarness) -> None:
        from explorer.constants import PLUGIN_NAME

        import load
        assert load.panel is not None
        assert load.panel.title_label.cget("text") == PLUGIN_NAME
        assert load.panel._title_font.actual("weight") == "bold"

    def test_header_credit_totals_show_zero_not_a_question_mark(self, plugin:TestHarness) -> None:
        """ _credits() shows "?" for 0 (unknown-vs-empty ambiguity elsewhere) -- but here 0
        pending is a real, known state, so the header should say "0 Cr", not "?". """
        import load
        assert load.panel is not None
        load.panel.refresh()
        assert load.panel.cart_value_label.cget("text") == "0 Cr"
        assert load.panel.exo_value_label.cget("text") == "0 Cr"

    def test_system_header_state_renders_bold(self, plugin:TestHarness) -> None:
        """ "SystemName — N bodies —" stays normal weight; only the state word is bold. """
        import tkinter.font as tkfont

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.panel is not None
        header_row = load.panel.scroll.interior.winfo_children()[0]
        prefix_cell, state_cell = header_row.winfo_children()
        assert tkfont.Font(font=prefix_cell.cget("font")).actual("weight") == "normal"
        assert tkfont.Font(font=state_cell.cget("font")).actual("weight") == "bold"
        assert state_cell.cget("text") == "Done"

    def test_toggle_hides_and_shows_the_scrollable_content(self, plugin:TestHarness) -> None:
        from explorer.ui.panel import PANEL_SHOWN_GLYPH, PANEL_HIDDEN_GLYPH

        import load
        assert load.panel is not None
        assert load.panel.scroll.winfo_manager() == "grid"
        assert load.panel.toggle_button.cget("text") == PANEL_SHOWN_GLYPH

        load.panel._toggle_panel()
        assert load.panel.scroll.winfo_manager() == ""
        assert load.panel.toggle_button.cget("text") == PANEL_HIDDEN_GLYPH

        load.panel._toggle_panel()
        assert load.panel.scroll.winfo_manager() == "grid"
        assert load.panel.toggle_button.cget("text") == PANEL_SHOWN_GLYPH

    def test_toggle_persists_across_the_config(self, plugin:TestHarness) -> None:
        from explorer.constants import CFG_PANEL_ENABLED

        import load
        assert load.panel is not None
        load.panel._toggle_panel()
        try:
            assert plugin.config.get_bool(CFG_PANEL_ENABLED) is False
        finally:
            load.panel._toggle_panel() # broad-impact flag -- must not leak to other tests

    def test_refresh_is_a_noop_while_hidden_and_catches_up_when_shown(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.panel is not None
        before:list[str] = _panel_lines(load)

        load.panel._toggle_panel() # hide
        assert load.explorer_state.system_id is not None
        load.store.update_system(load.explorer_state.system_id, honk_hint="worth a full scan")
        load.panel.refresh() # e.g. a journal-driven refresh() while hidden -- must not touch the UI
        assert _panel_lines(load) == before

        load.panel._toggle_panel() # show again -- must reflect the change made while hidden
        assert _panel_lines(load) != before

    def test_panel_starts_hidden_when_config_says_so(self, harness:TestHarness, tmp_path) -> None:
        from explorer.constants import CFG_PANEL_ENABLED
        from explorer.ui.panel import ExplorerPanel, PANEL_HIDDEN_GLYPH
        from explorer.db.store import ExplorerStore
        from explorer.state import ExplorerState

        harness.config.set(CFG_PANEL_ENABLED, False)
        store = ExplorerStore(tmp_path / "explorer_standalone.sqlite")
        try:
            panel = ExplorerPanel(harness.parent, store, ExplorerState())
            assert panel.scroll.winfo_manager() == ""
            assert panel.toggle_button.cget("text") == PANEL_HIDDEN_GLYPH
        finally:
            store.close()
            harness.config.set(CFG_PANEL_ENABLED, True)

class TestVisibleLinesConfig:

    def test_refresh_applies_configured_visible_lines(self, plugin:TestHarness) -> None:
        """ CFG_VISIBLE_LINES drives the scrollable frame's height live -- no restart needed. """
        from explorer.ui.panel import LINE_HEIGHT_PX

        import load
        assert load.panel is not None
        plugin.config.set("EDMCExplorerLite_VisibleLines", 8)
        load.panel.refresh()
        assert load.panel.scroll.cget('maxheight') == 8 * LINE_HEIGHT_PX

class TestPrefs:

    def test_build_and_save_roundtrip(self, plugin:TestHarness) -> None:
        from explorer.ui import prefs as prefs_ui
        from explorer.constants import CFG_SCAN_VALUE_THRESHOLD, CFG_OVERLAY_RADAR_ENABLED

        frame = prefs_ui.build_prefs(plugin.parent, "Testy", False)
        assert frame is not None

        prefs_ui._pref_vars[CFG_SCAN_VALUE_THRESHOLD].set("123456")
        prefs_ui._pref_vars[CFG_OVERLAY_RADAR_ENABLED].set(False)
        prefs_ui.save_prefs("Testy", False)

        assert plugin.config.get_int(CFG_SCAN_VALUE_THRESHOLD) == 123456
        assert plugin.config.get_bool(CFG_OVERLAY_RADAR_ENABLED) is False

    def test_invalid_threshold_falls_back_to_default(self, plugin:TestHarness) -> None:
        from explorer.ui import prefs as prefs_ui
        from explorer.constants import CFG_EXOBIO_VALUE_THRESHOLD, DEFAULT_EXOBIO_VALUE_THRESHOLD

        prefs_ui.build_prefs(plugin.parent, "Testy", False)
        prefs_ui._pref_vars[CFG_EXOBIO_VALUE_THRESHOLD].set("not-a-number")
        prefs_ui.save_prefs("Testy", False)

        assert plugin.config.get_int(CFG_EXOBIO_VALUE_THRESHOLD) == DEFAULT_EXOBIO_VALUE_THRESHOLD

    def test_header_shows_name_version_and_github_link(self, plugin:TestHarness) -> None:
        from explorer.ui import prefs as prefs_ui
        from explorer.constants import PLUGIN_NAME

        frame = prefs_ui.build_prefs(plugin.parent, "Testy", False, version="1.2.3")
        labels = {c.cget("text") for c in frame.winfo_children() if "text" in c.keys()}
        assert f"{PLUGIN_NAME} v1.2.3" in labels

        links = [c for c in frame.winfo_children() if type(c).__name__ == "HyperlinkLabel"]
        assert len(links) == 1 and links[0].cget("text") == "GitHub"
        assert links[0].url == prefs_ui.GH_URL

    def test_all_three_sections_are_present(self, plugin:TestHarness) -> None:
        from explorer.ui import prefs as prefs_ui

        frame = prefs_ui.build_prefs(plugin.parent, "Testy", False)
        labels = {c.cget("text") for c in frame.winfo_children() if "text" in c.keys()}
        assert {"Thresholds", "Overlays", "Debug"} <= labels

    def test_every_pref_still_has_a_live_widget(self, plugin:TestHarness) -> None:
        """ Regression guard for the two-up layout: every Pref must still end up with a
        variable in _pref_vars, however it's split across the left/right columns. """
        from explorer.ui import prefs as prefs_ui

        prefs_ui.build_prefs(plugin.parent, "Testy", False)
        assert set(prefs_ui._pref_vars.keys()) == {p.key for p in prefs_ui.PREFS}

    def test_overlays_section_disabled_without_an_overlay_backend(self, plugin:TestHarness) -> None:
        from explorer.ui import prefs as prefs_ui

        frame = prefs_ui.build_prefs(plugin.parent, "Testy", False, overlay_available=False)
        radar_cb = next(c for c in frame.winfo_children() if "text" in c.keys() and c.cget("text") == "Show radar on overlay")
        assert str(radar_cb.cget("state")) == "disabled"

        threshold_entry = next(c for c in frame.winfo_children() if type(c).__name__ == "EntryMenu")
        assert str(threshold_entry.cget("state")) == "normal" # Thresholds section is unaffected

    def test_overlays_section_enabled_with_an_overlay_backend(self, plugin:TestHarness) -> None:
        from explorer.ui import prefs as prefs_ui

        frame = prefs_ui.build_prefs(plugin.parent, "Testy", False, overlay_available=True)
        radar_cb = next(c for c in frame.winfo_children() if "text" in c.keys() and c.cget("text") == "Show radar on overlay")
        assert str(radar_cb.cget("state")) == "normal"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
