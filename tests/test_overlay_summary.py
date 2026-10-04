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
from explorer.state import state as explorer_state
from explorer.ui.overlay_summary import ANCHOR_X, CURRENT_BODY_INDENT_PX, ANCHOR_Y, HEADER_LINE_HEIGHT_PX, LINE_HEIGHT_PX
from explorer.util import now_iso
from explorer.constants import CFG_OVERLAY_SUMMARY_ENABLED, CFG_PANEL_ENABLED
import explorer.db.store as store_module
import explorer.session_persist as session_persist_module
from explorer.context import Context

@pytest.fixture
def plugin(harness:TestHarness, tmp_path, monkeypatch) -> Generator[TestHarness, None, None]:
    explorer_state.reset_all()

    monkeypatch.setattr(store_module, "resolve_db_path", lambda: tmp_path / "explorer.sqlite")

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
        assert Context.summary_overlay is not None and Context.store is not None
        Context.summary_overlay.render(Context.store, explorer_state) # must not raise
        assert Context.summary_overlay.overlay._overlay.messages == {}

    def test_render_shows_header_and_flagged_body_lines(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None and Context.panel is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        Context.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)

        Context.summary_overlay.render(Context.store, explorer_state)

        messages = Context.summary_overlay.overlay._overlay.messages
        header = messages[f"{FRAME_PREFIX}header"]
        # No system name -- it's already shown elsewhere in the game's own UI, see system_status_text()
        assert header[1] == "1 body — Done"

        body_line = messages[f"{FRAME_PREFIX}body-0"]
        assert body_line[1].startswith("A 1")
        assert "1M Cr" in body_line[1]

    def test_render_caps_body_lines_and_shows_an_overflow_count(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        for body_id in range(1, MAX_BODY_LINES + 3):
            body_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, body_id, f"QuietSpace A {body_id}")
            Context.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)

        Context.summary_overlay.render(Context.store, explorer_state)

        messages = Context.summary_overlay.overlay._overlay.messages
        assert f"{FRAME_PREFIX}body-{MAX_BODY_LINES - 1}" in messages
        assert f"{FRAME_PREFIX}body-{MAX_BODY_LINES}" not in messages
        assert messages[f"{FRAME_PREFIX}overflow"][1] == "+2 more"

    def test_flagged_bodies_within_a_group_are_ordered_by_distance(self, plugin:TestHarness) -> None:
        """ Distance, not body_id, breaks ties in each group. """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None

        far_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace 1")
        Context.store.update_body(far_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1, distance_ls=500)
        near_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 2, "QuietSpace 2")
        Context.store.update_body(near_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1, distance_ls=50)

        Context.summary_overlay.render(Context.store, explorer_state)

        messages = Context.summary_overlay.overlay._overlay.messages
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

        assert Context.store is not None and Context.summary_overlay is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        progress_id:int = Context.store.get_or_create_species_progress(body_pk, "Bacterium")
        Context.store.update_species_progress(progress_id, species="Bacterium Aurasus", samples_taken=2)

        explorer_state.body_id = 1
        explorer_state.body_name = "QuietSpace A 1"

        Context.summary_overlay.render(Context.store, explorer_state)

        messages = Context.summary_overlay.overlay._overlay.messages
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

        assert Context.store is not None and Context.summary_overlay is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        genera:list[str] = ["Bacterium", "Aleoida", "Fonticulua", "Tussock", "Osseus", "Stratum", "Recepta", "Clypeus"]
        for genus in genera:
            progress_id:int = Context.store.get_or_create_species_progress(body_pk, genus)
            Context.store.update_species_progress(progress_id, species=f"{genus} Test", samples_taken=1)

        explorer_state.body_id = 1
        explorer_state.body_name = "QuietSpace A 1"

        Context.summary_overlay.render(Context.store, explorer_state)

        messages = Context.summary_overlay.overlay._overlay.messages
        for i in range(len(genera)):
            assert f"{FRAME_PREFIX}current-{i}" in messages

    def test_current_body_section_hidden_once_fully_sampled(self, plugin:TestHarness) -> None:

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        progress_id:int = Context.store.get_or_create_species_progress(body_pk, "Bacterium")
        Context.store.update_species_progress(progress_id, species="Bacterium Aurasus", samples_taken=3, completed_at=now_iso())

        explorer_state.body_id = 1
        explorer_state.body_name = "QuietSpace A 1"

        Context.summary_overlay.render(Context.store, explorer_state)

        messages = Context.summary_overlay.overlay._overlay.messages
        assert f"{FRAME_PREFIX}current-0" not in messages

    def test_current_body_section_absent_off_foot_with_no_genus_known(self, plugin:TestHarness) -> None:
        """ Flying over a body with no confirmed genus and no prediction -- nothing worth
        showing yet, matching the panel's own gating. """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")

        explorer_state.body_id = 1
        explorer_state.body_name = "QuietSpace A 1"
        explorer_state.on_foot = False

        Context.summary_overlay.render(Context.store, explorer_state)

        messages = Context.summary_overlay.overlay._overlay.messages
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

        assert Context.store is not None and Context.summary_overlay is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        Context.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)

        Context.summary_overlay.render(Context.store, explorer_state)
        assert "A 1" in Context.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}body-0"][1]

        Context.store.update_body(body_pk, mapped_at="2026-01-01T00:00:00Z") # now mapped -- flagged_body_row drops it

        Context.summary_overlay.render(Context.store, explorer_state)
        assert Context.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}body-0"][1] == ""

    def test_overflow_line_clears_immediately_once_the_count_no_longer_needs_it(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pks:list[int] = []
        for body_id in range(1, MAX_BODY_LINES + 3):
            body_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, body_id, f"QuietSpace A {body_id}")
            Context.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)
            body_pks.append(body_pk)

        Context.summary_overlay.render(Context.store, explorer_state)
        assert Context.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}overflow"][1] == "+2 more"

        for body_pk in body_pks[MAX_BODY_LINES:]: # map away the overflow bodies
            Context.store.update_body(body_pk, mapped_at="2026-01-01T00:00:00Z")

        Context.summary_overlay.render(Context.store, explorer_state)
        assert Context.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}overflow"][1] == ""

    def test_current_body_line_clears_immediately_once_fully_sampled(self, plugin:TestHarness) -> None:

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        body_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        progress_id:int = Context.store.get_or_create_species_progress(body_pk, "Bacterium")
        Context.store.update_species_progress(progress_id, species="Bacterium Aurasus", samples_taken=2)

        explorer_state.body_id = 1
        explorer_state.body_name = "QuietSpace A 1"

        Context.summary_overlay.render(Context.store, explorer_state)
        assert "Bacterium" in Context.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}current-0"][1]

        Context.store.update_species_progress(progress_id, samples_taken=3, completed_at=now_iso())

        Context.summary_overlay.render(Context.store, explorer_state)
        assert Context.summary_overlay.overlay._overlay.messages[f"{FRAME_PREFIX}current-0"][1] == ""

    def test_current_body_detail_nests_under_its_own_row_not_the_end(self, plugin:TestHarness) -> None:
        """
        Real-world report: bodies 2a/2b/2c all had biology, landed on 2a, and the panel nested
        the species detail directly under 2a's own row while the overlay always appended it
        after the whole list instead -- render() must interleave, matching the panel exactly.
        """

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None
        assert explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        middle_pk:int|None = None
        for body_id in (1, 2, 3):
            body_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, body_id, f"QuietSpace A {body_id}")
            Context.store.update_body(body_pk, has_biological_signals=1, biological_signal_count=1)
            if body_id == 2: # landed here -- this is the one with in-progress sampling
                middle_pk = body_pk

        assert middle_pk is not None
        progress_id:int = Context.store.get_or_create_species_progress(middle_pk, "Bacterium")
        Context.store.update_species_progress(progress_id, species="Bacterium Aurasus", samples_taken=2)
        explorer_state.body_id = 2
        explorer_state.body_name = "QuietSpace A 2"

        Context.summary_overlay.render(Context.store, explorer_state)

        messages = Context.summary_overlay.overlay._overlay.messages
        base_y:int = ANCHOR_Y + HEADER_LINE_HEIGHT_PX
        assert "A 1" in messages[f"{FRAME_PREFIX}body-0"][1] and messages[f"{FRAME_PREFIX}body-0"][4] == base_y
        assert "A 2" in messages[f"{FRAME_PREFIX}body-1"][1] and messages[f"{FRAME_PREFIX}body-1"][4] == base_y + LINE_HEIGHT_PX
        assert "Bacterium Aurasus" in messages[f"{FRAME_PREFIX}current-0"][1]
        assert messages[f"{FRAME_PREFIX}current-0"][4] == base_y + LINE_HEIGHT_PX * 2
        assert "A 3" in messages[f"{FRAME_PREFIX}body-2"][1] # pushed down below the interleaved detail
        assert messages[f"{FRAME_PREFIX}body-2"][4] == base_y + LINE_HEIGHT_PX * 3

    def test_disabling_the_summary_mid_session_clears_everything_immediately(self, plugin:TestHarness) -> None:

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None and explorer_state.cmdr_id is not None
        assert explorer_state.system_id is not None
        body_pk:int = Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 1, "QuietSpace A 1")
        Context.store.update_body(body_pk, flagged_value=1, estimated_scan_value=1_000_000, was_discovered=1, was_mapped=1)

        Context.summary_overlay.render(Context.store, explorer_state)
        messages = Context.summary_overlay.overlay._overlay.messages
        assert messages[f"{FRAME_PREFIX}header"][1] != "" and messages[f"{FRAME_PREFIX}body-0"][1] != ""

        plugin.config.set(CFG_OVERLAY_SUMMARY_ENABLED, False)
        Context.summary_overlay.render(Context.store, explorer_state)

        assert messages[f"{FRAME_PREFIX}header"][1] == ""
        assert messages[f"{FRAME_PREFIX}body-0"][1] == ""

    def test_render_respects_summary_disabled_config(self, plugin:TestHarness) -> None:

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)
        plugin.config.set(CFG_OVERLAY_SUMMARY_ENABLED, False)

        assert Context.store is not None and Context.summary_overlay is not None
        Context.summary_overlay.render(Context.store, explorer_state)

        assert Context.summary_overlay.overlay._overlay.messages == {}

    def test_render_is_a_noop_while_docked(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None
        explorer_state.docked = True
        Context.summary_overlay.render(Context.store, explorer_state)

        assert Context.summary_overlay.overlay._overlay.messages == {}

    def test_render_is_a_noop_on_foot_in_a_station(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None
        explorer_state.on_foot_in_station = True
        Context.summary_overlay.render(Context.store, explorer_state)

        assert Context.summary_overlay.overlay._overlay.messages == {}

    def test_render_is_a_noop_while_a_ui_panel_has_focus(self, plugin:TestHarness) -> None:
        """ e.g. galaxy map / system map open in the ship -- GuiFocus != 0. """
        from edmc_data import GuiFocusGalaxyMap # type: ignore

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        assert Context.store is not None and Context.summary_overlay is not None
        explorer_state.gui_focus = GuiFocusGalaxyMap
        Context.summary_overlay.render(Context.store, explorer_state)

        assert Context.summary_overlay.overlay._overlay.messages == {}

    def test_render_respects_panel_hidden_via_show_hide_toggle(self, plugin:TestHarness) -> None:

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)
        plugin.config.set(CFG_PANEL_ENABLED, False)
        try:
            assert Context.store is not None and Context.summary_overlay is not None
            Context.summary_overlay.render(Context.store, explorer_state)

            assert Context.summary_overlay.overlay._overlay.messages == {}
        finally:
            plugin.config.set(CFG_PANEL_ENABLED, True) # broad-impact flag -- must not leak to other tests

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
