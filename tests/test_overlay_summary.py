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
        assert header[1] == "1 body — done"

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
        Real-world regression: mapping a body drops it from the panel's list synchronously
        (on_saa_scan_complete only returns {"panel": True}), but the overlay only used to stop
        RE-SENDING that body's frame, relying on its own TTL to make it disappear -- fine at the
        original 8s TTL, but after bumping TTL to 30s (see the "stay on screen longer" fix) a
        mapped body's stale line could visibly linger for up to that long. render() must now
        explicitly clear a dropped slot the moment it notices, not just stop refreshing it.
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

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
