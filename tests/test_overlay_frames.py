"""
Unit tests for the overlay radar (explorer/ui/overlay_frames.py).

Run with:
    .venv/bin/python -m pytest tests/test_overlay_frames.py -v --tb=short

`harness` (session-scoped, one shared Tk root) comes from conftest.py. Overlay backend mode
is switched per-test via TestHarness.set_overlay_mode() (a runtime call, not the constructor
kwarg) since the harness is already constructed by the time any test runs.
"""
import math
import pytest
from typing import Generator

from harness import TestHarness, reset_plugin_modules

from explorer.db.store import ExplorerStore
from explorer.utils.overlay import Overlay
from explorer.state import ExplorerState
from explorer.ui.overlay_frames import RadarOverlay, FRAME_PREFIX, CENTER_X, CENTER_Y, SAMPLE_COLOR

@pytest.fixture
def overlay_mode(request, harness:TestHarness) -> Generator[None, None, None]:
    marker = request.node.get_closest_marker('overlay')
    harness.set_overlay_mode(marker.args[0] if marker else 'All')
    yield
    harness.set_overlay_mode('All')

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

def _landed_state(store:ExplorerStore, genus:str = "Bacterium", samples:int = 1, mark_done:bool = False) -> ExplorerState:
    """ A Cmdr standing on a body whose genus was already revealed via SAASignalsFound (in the
    DB) -- samples/mark_done additionally simulate 0+ ScanOrganic calls made so far this visit. """
    state = ExplorerState()
    state.cmdr_id = store.get_or_create_cmdr("Testy")
    state.system_id = store.get_or_create_system(state.cmdr_id, 1, "Deltius")
    state.landed = True
    state.on_foot = True
    state.body_id = 2
    state.body_name = "Deltius 2"
    state.has_lat_long = True
    state.latitude = 10.0
    state.longitude = 20.0
    state.heading = 90.0
    state.altitude = 0.0
    state.planet_radius = 500_000.0

    body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
    progress_id:int = store.get_or_create_species_progress(body_pk, genus)
    if mark_done:
        store.update_species_progress(progress_id, completed_at="2026-01-01T00:00:00Z")
    if samples:
        state.sample_positions[genus] = [(10.0 + i * 0.0001, 20.0) for i in range(samples)]
    return state

def _flying_state(store:ExplorerStore) -> ExplorerState:
    """ Dropped out of supercruise over a body's surface, still in the ship -- not landed, not
    on-foot, no samples possible yet, but a body/lat-long context already exists. """
    state = ExplorerState()
    state.cmdr_id = store.get_or_create_cmdr("Testy")
    state.system_id = store.get_or_create_system(state.cmdr_id, 1, "Deltius")
    state.body_id = 2
    state.body_name = "Deltius 2"
    state.has_lat_long = True
    state.latitude = 10.0
    state.longitude = 20.0
    state.heading = 90.0
    return state

class TestRadarOverlayNoOverlay:

    @pytest.mark.overlay('None')
    def test_render_is_a_safe_noop_without_overlay(self, overlay_mode, store:ExplorerStore) -> None:
        radar = RadarOverlay(Overlay())
        radar.render(store, _landed_state(store)) # must not raise

    @pytest.mark.overlay('None')
    def test_render_is_a_noop_with_no_context_at_all(self, overlay_mode, store:ExplorerStore) -> None:
        radar = RadarOverlay(Overlay())
        radar.render(store, ExplorerState()) # no cmdr/system/body/lat-long -- must not raise

class TestRadarOverlayModern:

    @pytest.mark.overlay('Modern')
    def test_render_draws_rings_player_and_samples(self, overlay_mode, store:ExplorerStore) -> None:
        radar = RadarOverlay(Overlay())
        state = _landed_state(store, samples=2)
        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}ring-1.0" in shapes
        assert f"{FRAME_PREFIX}ring-active-Bacterium" in shapes # Bacterium's 500m min-distance fits within the fixed 1500m display range
        assert f"{FRAME_PREFIX}player" in shapes
        assert f"{FRAME_PREFIX}sample-Bacterium-0" in shapes
        assert f"{FRAME_PREFIX}sample-Bacterium-1" in shapes

    @pytest.mark.overlay('Modern')
    def test_render_rotates_sample_positions_to_current_heading(self, overlay_mode, store:ExplorerStore) -> None:
        """
        Heading-up: the player's facing direction always maps to screen "up". A sample due north
        of the player should appear straight above center while facing north (heading 0), but
        straight to the LEFT of center while facing east (heading 90) -- north is to your left
        when you're facing east.
        """
        radar = RadarOverlay(Overlay())

        state = _landed_state(store, samples=0)
        state.heading = 0.0
        state.sample_positions["Bacterium"] = [(10.01, 20.0)] # ~87m due north of the player
        radar.render(store, state)
        shape = radar.overlay._overlay.shapes[f"{FRAME_PREFIX}sample-Bacterium-0"]
        sx, sy, w, h = shape[4], shape[5], shape[6], shape[7]
        cx, cy = sx + w / 2, sy + h / 2
        assert cy < CENTER_Y # above center
        assert round(cx) == CENTER_X

        state.heading = 90.0
        radar.render(store, state)
        shape = radar.overlay._overlay.shapes[f"{FRAME_PREFIX}sample-Bacterium-0"]
        sx, sy, w, h = shape[4], shape[5], shape[6], shape[7]
        cx, cy = sx + w / 2, sy + h / 2
        assert cx < CENTER_X # left of center
        assert round(cy) == CENTER_Y

    @pytest.mark.overlay('Modern')
    def test_render_draws_every_incomplete_confirmed_genus_at_once(self, overlay_mode, store:ExplorerStore) -> None:
        """
        Regression: render() used to pick a single "active genus" (the first not-yet-completed
        row in DB insertion order) and only ever drew that one's ring/samples -- so a second
        confirmed, still-incomplete genus on the same body (tagged via SAASignalsFound) never
        showed up at all, and if that second genus happened to sort first, even the FIRST
        genus's own already-taken samples would be hidden. Both should now draw simultaneously.
        """
        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=1)
        state.sample_positions["Fonticulua"] = [(10.0001, 20.0)]
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.get_or_create_species_progress(body_pk, "Fonticulua")

        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}ring-active-Bacterium" in shapes
        assert f"{FRAME_PREFIX}ring-active-Fonticulua" in shapes
        assert f"{FRAME_PREFIX}sample-Bacterium-0" in shapes
        assert f"{FRAME_PREFIX}sample-Fonticulua-0" in shapes

    @pytest.mark.overlay('Modern')
    def test_render_distinguishes_in_progress_from_tagged_unstarted_genus(self, overlay_mode, store:ExplorerStore) -> None:
        """
        A genus with a sample already taken this visit ("in progress") gets the orange ring and
        its sample markers; a genus that's merely confirmed (SAASignalsFound) but not yet
        approached this visit gets a different ring color and a short text label instead, so two
        simultaneously-tagged species don't look identical on the radar.
        """
        from explorer.ui.overlay_frames import ACTIVE_RING_COLOR, TAGGED_RING_COLOR

        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=1)
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.get_or_create_species_progress(body_pk, "Fonticulua") # tagged, no sample taken yet

        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        messages = radar.overlay._overlay.messages
        assert shapes[f"{FRAME_PREFIX}ring-active-Bacterium"][0]["color"] == ACTIVE_RING_COLOR
        assert shapes[f"{FRAME_PREFIX}ring-active-Fonticulua"][0]["color"] == TAGGED_RING_COLOR
        assert messages[f"{FRAME_PREFIX}label-Fonticulua"][1] == "FON"
        assert f"{FRAME_PREFIX}sample-Fonticulua-0" not in shapes # nothing taken yet -- nothing to draw

    @pytest.mark.overlay('Modern')
    def test_render_clamps_out_of_range_sample_to_ring_edge_and_hollows_it(self, overlay_mode, store:ExplorerStore) -> None:
        """
        Regression: a sample position outside the display range used to keep drifting further
        from center in screen-space as the player walked away, well past the radar's own edge.
        It should instead clamp to the ring's edge (same bearing) and render hollow (border only,
        no fill) to signal "direction only, not an exact fix" instead of a false-precision dot.
        """
        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=0)
        state.sample_positions["Bacterium"] = [(10.23, 20.0)] # ~2007m north -- past the fixed 1500m display range

        radar.render(store, state)

        shape = radar.overlay._overlay.shapes[f"{FRAME_PREFIX}sample-Bacterium-0"]
        border_color, fill_color, sx, sy, w, h = shape[2], shape[3], shape[4], shape[5], shape[6], shape[7]
        assert border_color == SAMPLE_COLOR
        assert fill_color == "" # hollow

        cx, cy = sx + w / 2, sy + h / 2
        assert round(math.hypot(cx - CENTER_X, cy - CENTER_Y)) == 150 # clamped to the (default) radar radius

    @pytest.mark.overlay('Modern')
    def test_render_draws_rings_before_any_sample_is_taken(self, overlay_mode, store:ExplorerStore) -> None:
        """
        Regression test: the active genus used to come from state.sample_positions, which is
        session-only and only gains an entry once ScanOrganic fires for the FIRST sample -- so
        the radar drew nothing at all while walking towards the first sample spot, exactly when
        it's most needed. Genus now comes from the DB (SAASignalsFound, set while still in
        orbit), so rings must show up here with zero samples taken.
        """
        radar = RadarOverlay(Overlay())
        state = _landed_state(store, samples=0)
        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}ring-1.0" in shapes
        assert f"{FRAME_PREFIX}ring-active-Bacterium" in shapes
        assert f"{FRAME_PREFIX}player" in shapes

    @pytest.mark.overlay('Modern')
    def test_render_draws_rings_while_flying_over_surface_not_landed(self, overlay_mode, store:ExplorerStore) -> None:
        """
        Regression test: the radar used to require landed AND on_foot, so it stayed dark from
        SupercruiseExit all the way down to actually stepping outside -- useless for the part of
        the approach where you're deciding whether/where to land. A confirmed genus already in
        the DB (SAASignalsFound, from orbit) should draw rings while still flying.
        """
        radar = RadarOverlay(Overlay())
        state = _flying_state(store)
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.get_or_create_species_progress(body_pk, "Bacterium")

        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}ring-1.0" in shapes
        assert f"{FRAME_PREFIX}player" in shapes

    @pytest.mark.overlay('Modern')
    def test_render_draws_rings_from_predicted_genus_before_confirmation(self, overlay_mode, store:ExplorerStore) -> None:
        """ Before SAASignalsFound even happens -- a pre-DSS genus prediction (from Scan alone)
        is still useful while approaching, so it's the fallback when there's no confirmed genus yet. """
        radar = RadarOverlay(Overlay())
        state = _flying_state(store)
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.replace_genus_predictions(body_pk, [("Bacterium", None, 0.8)])

        radar.render(store, state)

        assert f"{FRAME_PREFIX}ring-1.0" in radar.overlay._overlay.shapes

    @pytest.mark.overlay('Modern')
    def test_render_is_a_noop_when_no_genus_known_at_all(self, overlay_mode, store:ExplorerStore) -> None:
        """ Flying over a body with no confirmed or predicted genus -- nothing useful to show yet. """
        radar = RadarOverlay(Overlay())
        radar.render(store, _flying_state(store))
        assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.shapes

    @pytest.mark.overlay('Modern')
    def test_render_is_a_noop_without_lat_long(self, overlay_mode, store:ExplorerStore) -> None:
        radar = RadarOverlay(Overlay())
        state = _landed_state(store)
        state.has_lat_long = False
        radar.render(store, state)
        assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.shapes

    @pytest.mark.overlay('Modern')
    def test_render_respects_configured_radar_size(self, overlay_mode, harness:TestHarness, store:ExplorerStore) -> None:
        from explorer.constants import CFG_OVERLAY_RADAR_SIZE
        harness.config.set(CFG_OVERLAY_RADAR_SIZE, 300)
        try:
            radar = RadarOverlay(Overlay())
            state = _landed_state(store, samples=0)
            radar.render(store, state)

            msg, _ = radar.overlay._overlay.shapes[f"{FRAME_PREFIX}ring-1.0"]
            assert msg["vector"][0]["x"] - CENTER_X == 300 # full-scale ring radius == the configured size
        finally:
            harness.config.set(CFG_OVERLAY_RADAR_SIZE, 150)

    @pytest.mark.overlay('Modern')
    def test_render_respects_radar_disabled_config(self, overlay_mode, harness:TestHarness, store:ExplorerStore) -> None:
        from explorer.constants import CFG_OVERLAY_RADAR_ENABLED
        harness.config.set(CFG_OVERLAY_RADAR_ENABLED, False)
        try:
            radar = RadarOverlay(Overlay())
            radar.render(store, _landed_state(store))
            assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.shapes
        finally:
            harness.config.set(CFG_OVERLAY_RADAR_ENABLED, True)

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
