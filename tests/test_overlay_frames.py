"""
Unit tests for the overlay radar (explorer/ui/overlay_frames.py).

Run with:
    .venv/bin/python -m pytest tests/test_overlay_frames.py -v --tb=short

`harness` (session-scoped, one shared Tk root) comes from conftest.py. Overlay backend mode
is switched per-test via TestHarness.set_overlay_mode() (a runtime call, not the constructor
kwarg) since the harness is already constructed by the time any test runs.
"""
import pytest
from typing import Generator

from harness import TestHarness, reset_plugin_modules

from explorer.db.store import ExplorerStore
from explorer.utils.overlay import Overlay
from explorer.state import ExplorerState
from explorer.ui.overlay_frames import RadarOverlay, FRAME_PREFIX

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
        assert f"{FRAME_PREFIX}ring-active" in shapes # Bacterium's 500m min-distance fits within a 750m display range
        assert f"{FRAME_PREFIX}player" in shapes
        assert f"{FRAME_PREFIX}heading" in shapes
        assert f"{FRAME_PREFIX}sample-0" in shapes
        assert f"{FRAME_PREFIX}sample-1" in shapes

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
        assert f"{FRAME_PREFIX}ring-active" in shapes
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
