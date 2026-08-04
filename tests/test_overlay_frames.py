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

from explorer.utils.overlay import Overlay
from explorer.state import ExplorerState
from explorer.ui.overlay_frames import RadarOverlay, FRAME_PREFIX

@pytest.fixture
def overlay_mode(request, harness:TestHarness) -> Generator[None, None, None]:
    marker = request.node.get_closest_marker('overlay')
    harness.set_overlay_mode(marker.args[0] if marker else 'All')
    yield
    harness.set_overlay_mode('All')

def _landed_state(genus:str = "Bacterium", samples:int = 1) -> ExplorerState:
    state = ExplorerState()
    state.landed = True
    state.on_foot = True
    state.body_id = 2
    state.has_lat_long = True
    state.latitude = 10.0
    state.longitude = 20.0
    state.heading = 90.0
    state.altitude = 0.0
    state.planet_radius = 500_000.0
    state.sample_positions[genus] = [(10.0 + i * 0.0001, 20.0) for i in range(samples)]
    return state

class TestRadarOverlayNoOverlay:

    @pytest.mark.overlay('None')
    def test_render_is_a_safe_noop_without_overlay(self, overlay_mode) -> None:
        radar = RadarOverlay(Overlay())
        radar.render(_landed_state()) # must not raise

    @pytest.mark.overlay('None')
    def test_render_is_a_noop_when_not_exobiology_relevant(self, overlay_mode) -> None:
        radar = RadarOverlay(Overlay())
        radar.render(ExplorerState()) # not landed/on_foot -- must not raise

class TestRadarOverlayModern:

    @pytest.mark.overlay('Modern')
    def test_render_draws_rings_player_and_samples(self, overlay_mode) -> None:
        radar = RadarOverlay(Overlay())
        state = _landed_state(samples=2)
        radar.render(state)

        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}ring-1.0" in shapes
        assert f"{FRAME_PREFIX}ring-active" in shapes # Bacterium's 500m min-distance fits within a 750m display range
        assert f"{FRAME_PREFIX}player" in shapes
        assert f"{FRAME_PREFIX}heading" in shapes
        assert f"{FRAME_PREFIX}sample-0" in shapes
        assert f"{FRAME_PREFIX}sample-1" in shapes

    @pytest.mark.overlay('Modern')
    def test_render_is_a_noop_without_lat_long(self, overlay_mode) -> None:
        radar = RadarOverlay(Overlay())
        state = _landed_state()
        state.has_lat_long = False
        radar.render(state)
        assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.shapes

    @pytest.mark.overlay('Modern')
    def test_render_respects_radar_disabled_config(self, overlay_mode, harness:TestHarness) -> None:
        from explorer.constants import CFG_OVERLAY_RADAR_ENABLED
        harness.config.set(CFG_OVERLAY_RADAR_ENABLED, False)
        try:
            radar = RadarOverlay(Overlay())
            radar.render(_landed_state())
            assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.shapes
        finally:
            harness.config.set(CFG_OVERLAY_RADAR_ENABLED, True)

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
