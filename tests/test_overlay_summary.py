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
        # No system name -- it's already shown elsewhere in the game's own UI, see system_status_text()
        assert header[1] == "1 body — Done"

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

    def test_biologically_interesting_bodies_are_never_pushed_into_overflow(self, plugin:TestHarness) -> None:
        """
        Real-world report: a biological signal went missing from the overlay in a system with
        several cartography-flagged bodies. MAX_BODY_LINES is a hard cap with no scrolling, and
        the list used to be plain body_id order -- a body with confirmed biology but a higher
        body_id than several cartography-only bodies could get silently bumped into the
        anonymous "+N more" count. Biological interest must always sort first.
        """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None

        for body_id in range(1, MAX_BODY_LINES + 1): # low body_id, cartography-only -- would fill every slot
            body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, body_id, f"QuietSpace {body_id}")
            load.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)

        bio_body_id:int = MAX_BODY_LINES + 5 # high body_id -- last in plain body_id order
        bio_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, bio_body_id, "QuietSpace Bio")
        load.store.update_body(bio_pk, has_biological_signals=1, biological_signal_count=3)

        load.summary_overlay.render(load.store, load.explorer_state)

        messages = load.summary_overlay.overlay._overlay.messages
        shown_lines = [messages[f"{FRAME_PREFIX}body-{i}"][1] for i in range(MAX_BODY_LINES)]
        assert any("Bio" in line for line in shown_lines), shown_lines

    def test_flagged_bodies_within_a_group_are_ordered_by_distance(self, plugin:TestHarness) -> None:
        """ Distance, not body_id, breaks ties in each group. """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None

        far_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 1, "QuietSpace 1")
        load.store.update_body(far_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1, distance_ls=500)
        near_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 2, "QuietSpace 2")
        load.store.update_body(near_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1, distance_ls=50)

        load.summary_overlay.render(load.store, load.explorer_state)

        messages = load.summary_overlay.overlay._overlay.messages
        assert messages[f"{FRAME_PREFIX}body-0"][1].startswith("2 ") # nearer body (50ls) leads

    def test_render_shows_current_body_species_progress(self, plugin:TestHarness) -> None:
        """
        Real feature gap: the overlay only ever mirrored the top-level flagged-body list, never
        the per-species detail for whichever body you're actually standing on -- the panel's
        own nested table (ExplorerPanel._render_exobiology_section()). Reuses
        _exobio_progress_row() directly so the wording/values can't drift from the panel. No
        header line, same as the panel's own nesting -- just indented under the body above it.
        """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        from explorer.ui.overlay_summary import ANCHOR_X, CURRENT_BODY_INDENT_PX
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 1, "QuietSpace A 1")
        progress_id:int = load.store.get_or_create_species_progress(body_pk, "Bacterium")
        load.store.update_species_progress(progress_id, species="Bacterium Aurasus", samples_taken=2)

        load.explorer_state.body_id = 1
        load.explorer_state.body_name = "QuietSpace A 1"

        load.summary_overlay.render(load.store, load.explorer_state)

        messages = load.summary_overlay.overlay._overlay.messages
        current_line = messages[f"{FRAME_PREFIX}current-0"]
        assert "Bacterium Aurasus" in current_line[1]
        assert "2/3" in current_line[1]
        assert current_line[3] == ANCHOR_X + CURRENT_BODY_INDENT_PX # indented, not at the left margin

    def test_current_body_species_are_not_truncated(self, plugin:TestHarness) -> None:
        """ Unlike the flagged-body list (capped, with a "+N
        more" hint), the current body's species list has no
        overflow indicator -- every genus must show. """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 1, "QuietSpace A 1")
        genera:list[str] = ["Bacterium", "Aleoida", "Fonticulua", "Tussock", "Osseus", "Stratum", "Recepta", "Clypeus"]
        for genus in genera:
            progress_id:int = load.store.get_or_create_species_progress(body_pk, genus)
            load.store.update_species_progress(progress_id, species=f"{genus} Test", samples_taken=1)

        load.explorer_state.body_id = 1
        load.explorer_state.body_name = "QuietSpace A 1"

        load.summary_overlay.render(load.store, load.explorer_state)

        messages = load.summary_overlay.overlay._overlay.messages
        for i in range(len(genera)):
            assert f"{FRAME_PREFIX}current-{i}" in messages

    def test_current_body_section_hidden_once_fully_sampled(self, plugin:TestHarness) -> None:
        from explorer.util import now_iso

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 1, "QuietSpace A 1")
        progress_id:int = load.store.get_or_create_species_progress(body_pk, "Bacterium")
        load.store.update_species_progress(progress_id, species="Bacterium Aurasus", samples_taken=3, completed_at=now_iso())

        load.explorer_state.body_id = 1
        load.explorer_state.body_name = "QuietSpace A 1"

        load.summary_overlay.render(load.store, load.explorer_state)

        messages = load.summary_overlay.overlay._overlay.messages
        assert f"{FRAME_PREFIX}current-0" not in messages

    def test_current_body_section_absent_off_foot_with_no_genus_known(self, plugin:TestHarness) -> None:
        """ Flying over a body with no confirmed genus and no prediction -- nothing worth
        showing yet, matching the panel's own gating. """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None
        load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 1, "QuietSpace A 1")

        load.explorer_state.body_id = 1
        load.explorer_state.body_name = "QuietSpace A 1"
        load.explorer_state.on_foot = False

        load.summary_overlay.render(load.store, load.explorer_state)

        messages = load.summary_overlay.overlay._overlay.messages
        assert f"{FRAME_PREFIX}current-0" not in messages

    def test_a_body_dropping_off_the_list_clears_immediately_not_after_ttl(self, plugin:TestHarness) -> None:
        """
        Real-world regression: mapping a body drops it from the panel's list synchronously,
        but the overlay only used to stop RE-SENDING that body's frame, relying on its own TTL
        to make it disappear -- fine at the original 8s TTL, but after bumping TTL to 30s (see
        the "stay on screen longer" fix) a mapped body's stale line could visibly linger for up
        to that long. render() must now explicitly clear a dropped slot the moment it notices a
        body dropped out of the flagged list, not just stop refreshing it.
        """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)

        load.summary_overlay.render(load.store, load.explorer_state)
        assert "A 1" in load.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}body-0"][1]

        load.store.update_body(body_pk, mapped_at="2026-01-01T00:00:00Z") # now mapped -- flagged_body_row drops it

        load.summary_overlay.render(load.store, load.explorer_state)
        assert load.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}body-0"][1] == ""

    def test_overflow_line_clears_immediately_once_the_count_no_longer_needs_it(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None
        body_pks:list[int] = []
        for body_id in range(1, MAX_BODY_LINES + 3):
            body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, body_id, f"QuietSpace A {body_id}")
            load.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)
            body_pks.append(body_pk)

        load.summary_overlay.render(load.store, load.explorer_state)
        assert load.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}overflow"][1] == "+2 more"

        for body_pk in body_pks[MAX_BODY_LINES:]: # map away the overflow bodies
            load.store.update_body(body_pk, mapped_at="2026-01-01T00:00:00Z")

        load.summary_overlay.render(load.store, load.explorer_state)
        assert load.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}overflow"][1] == ""

    def test_current_body_line_clears_immediately_once_fully_sampled(self, plugin:TestHarness) -> None:
        from explorer.util import now_iso

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 1, "QuietSpace A 1")
        progress_id:int = load.store.get_or_create_species_progress(body_pk, "Bacterium")
        load.store.update_species_progress(progress_id, species="Bacterium Aurasus", samples_taken=2)

        load.explorer_state.body_id = 1
        load.explorer_state.body_name = "QuietSpace A 1"

        load.summary_overlay.render(load.store, load.explorer_state)
        assert "Bacterium" in load.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}current-0"][1]

        load.store.update_species_progress(progress_id, samples_taken=3, completed_at=now_iso())

        load.summary_overlay.render(load.store, load.explorer_state)
        assert load.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}current-0"][1] == ""

    def test_current_body_detail_nests_under_its_own_row_not_the_end(self, plugin:TestHarness) -> None:
        """
        Real-world report: bodies 2a/2b/2c all had biology, landed on 2a, and the panel nested
        the species detail directly under 2a's own row while the overlay always appended it
        after the whole list instead -- render() must interleave, matching the panel exactly.
        """
        from explorer.ui.overlay_summary import ANCHOR_Y, HEADER_LINE_HEIGHT_PX, LINE_HEIGHT_PX

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None
        assert load.explorer_state.cmdr_id is not None and load.explorer_state.system_id is not None
        for body_id in (1, 2, 3):
            body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, body_id, f"QuietSpace A {body_id}")
            load.store.update_body(body_pk, has_biological_signals=1, biological_signal_count=1)
            if body_id == 2: # landed here -- this is the one with in-progress sampling
                middle_pk = body_pk

        progress_id:int = load.store.get_or_create_species_progress(middle_pk, "Bacterium")
        load.store.update_species_progress(progress_id, species="Bacterium Aurasus", samples_taken=2)
        load.explorer_state.body_id = 2
        load.explorer_state.body_name = "QuietSpace A 2"

        load.summary_overlay.render(load.store, load.explorer_state)

        messages = load.summary_overlay.overlay._overlay.messages
        base_y:int = ANCHOR_Y + HEADER_LINE_HEIGHT_PX
        assert "A 1" in messages[f"{FRAME_PREFIX}body-0"][1] and messages[f"{FRAME_PREFIX}body-0"][4] == base_y
        assert "A 2" in messages[f"{FRAME_PREFIX}body-1"][1] and messages[f"{FRAME_PREFIX}body-1"][4] == base_y + LINE_HEIGHT_PX
        assert "Bacterium Aurasus" in messages[f"{FRAME_PREFIX}current-0"][1]
        assert messages[f"{FRAME_PREFIX}current-0"][4] == base_y + LINE_HEIGHT_PX * 2
        assert "A 3" in messages[f"{FRAME_PREFIX}body-2"][1] # pushed down below the interleaved detail
        assert messages[f"{FRAME_PREFIX}body-2"][4] == base_y + LINE_HEIGHT_PX * 3

    def test_disabling_the_summary_mid_session_clears_everything_immediately(self, plugin:TestHarness) -> None:
        from explorer.constants import CFG_OVERLAY_SUMMARY_ENABLED

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.store is not None and load.summary_overlay is not None and load.explorer_state.cmdr_id is not None
        assert load.explorer_state.system_id is not None
        body_pk:int = load.store.get_or_create_body(load.explorer_state.cmdr_id, load.explorer_state.system_id, 1, "QuietSpace A 1")
        load.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)

        load.summary_overlay.render(load.store, load.explorer_state)
        messages = load.summary_overlay.overlay._overlay.messages
        assert messages[f"{FRAME_PREFIX}header"][1] != "" and messages[f"{FRAME_PREFIX}body-0"][1] != ""

        plugin.config.set(CFG_OVERLAY_SUMMARY_ENABLED, False)
        load.summary_overlay.render(load.store, load.explorer_state)

        assert messages[f"{FRAME_PREFIX}header"][1] == ""
        assert messages[f"{FRAME_PREFIX}body-0"][1] == ""

    def test_render_respects_summary_disabled_config(self, plugin:TestHarness) -> None:
        from explorer.constants import CFG_OVERLAY_SUMMARY_ENABLED

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)
        plugin.config.set(CFG_OVERLAY_SUMMARY_ENABLED, False)

        import load
        assert load.store is not None and load.summary_overlay is not None
        load.summary_overlay.render(load.store, load.explorer_state)

        assert load.summary_overlay.overlay._overlay.messages == {}

    def test_render_is_a_noop_while_docked(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.summary_overlay is not None
        load.explorer_state.docked = True
        load.summary_overlay.render(load.store, load.explorer_state)

        assert load.summary_overlay.overlay._overlay.messages == {}

    def test_render_is_a_noop_on_foot_in_a_station(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.summary_overlay is not None
        load.explorer_state.on_foot_in_station = True
        load.summary_overlay.render(load.store, load.explorer_state)

        assert load.summary_overlay.overlay._overlay.messages == {}

    def test_render_is_a_noop_while_a_ui_panel_has_focus(self, plugin:TestHarness) -> None:
        """ e.g. galaxy map / system map open in the ship -- GuiFocus != 0. """
        from edmc_data import GuiFocusGalaxyMap # type: ignore

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        assert load.summary_overlay is not None
        load.explorer_state.gui_focus = GuiFocusGalaxyMap
        load.summary_overlay.render(load.store, load.explorer_state)

        assert load.summary_overlay.overlay._overlay.messages == {}

    def test_render_respects_panel_hidden_via_show_hide_toggle(self, plugin:TestHarness) -> None:
        from explorer.constants import CFG_PANEL_ENABLED

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)
        plugin.config.set(CFG_PANEL_ENABLED, False)
        try:
            import load
            assert load.store is not None and load.summary_overlay is not None
            load.summary_overlay.render(load.store, load.explorer_state)

            assert load.summary_overlay.overlay._overlay.messages == {}
        finally:
            plugin.config.set(CFG_PANEL_ENABLED, True) # broad-impact flag -- must not leak to other tests

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
