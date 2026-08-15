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
        state.sample_positions[genus] = [(10.0 + i * 0.0001, 20.0, None) for i in range(samples)]
        state.current_genus = genus
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
    def test_codex_tagged_sample_is_a_triangle_in_its_variant_color(self, overlay_mode, store:ExplorerStore) -> None:
        """
        A CodexEntry waypoint tag used to look identical to a real sample -- both drawn as the
        same filled square in SAMPLE_COLOR. A tag now draws as a hollow TRIANGLE in the game's
        own reported variant color (state.py's sample_positions third element) instead --
        shape, not just color, is what keeps it from ever being mistaken for a real sample.
        """
        from explorer.ui.overlay_frames import CODEX_TAG_COLORS

        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=1) # a real sample -- (lat, lon, None)
        state.sample_positions["Bacterium"].append((10.0002, 20.0, "Lime")) # a codex-tagged waypoint

        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        real_sample = shapes[f"{FRAME_PREFIX}sample-Bacterium-0"]
        assert real_sample[1] == "rect"
        assert real_sample[2] == SAMPLE_COLOR

        tagged_msg, _ = shapes[f"{FRAME_PREFIX}sample-Bacterium-1"]
        assert tagged_msg["shape"] == "vect"
        assert tagged_msg["color"] == CODEX_TAG_COLORS["Lime"]
        assert tagged_msg["fill"] == "" # always hollow
        assert len(tagged_msg["vector"]) == 4 # 3 triangle vertices + closing point back to the first

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
        state.sample_positions["Bacterium"] = [(10.01, 20.0, None)] # ~87m due north of the player
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
    def test_render_draws_samples_for_every_in_progress_genus_but_only_one_ring(self, overlay_mode, store:ExplorerStore) -> None:
        """
        Regression: render() used to pick a single "active genus" (the first not-yet-completed
        row in DB insertion order) and only ever drew that one's ring/samples -- so a second
        confirmed, still-incomplete genus on the same body (tagged via SAASignalsFound) never
        showed up at all, and if that second genus happened to sort first, even the FIRST
        genus's own already-taken samples would be hidden. Both genera's samples now always
        draw -- but only ONE ring shows at a time (state.current_genus, whichever you're
        actually sampling), since a ring per simultaneously-in-progress genus became illegible.
        """
        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=1) # sets current_genus = "Bacterium"
        state.sample_positions["Fonticulua"] = [(10.0001, 20.0, None)]
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.get_or_create_species_progress(body_pk, "Fonticulua")

        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}ring-active-Bacterium" in shapes # current_genus -- gets the ring
        assert f"{FRAME_PREFIX}ring-active-Fonticulua" not in shapes # in progress too, but not current -- no ring
        assert f"{FRAME_PREFIX}sample-Bacterium-0" in shapes
        assert f"{FRAME_PREFIX}sample-Fonticulua-0" in shapes # samples still show for both

    @pytest.mark.overlay('Modern')
    def test_render_shows_nothing_for_a_tagged_but_unstarted_genus(self, overlay_mode, store:ExplorerStore) -> None:
        """
        A genus merely confirmed (SAASignalsFound) but with no sample taken yet this visit has no
        known bearing -- only a distance -- so it draws nothing at all (no ring, no label): an
        earlier version drew a differently-colored ring + label for it, but that either had no
        real information to convey or (once heading-up was added) misleadingly suggested a
        direction. Only the genus actually being sampled gets a ring + markers.
        """
        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=1)
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.get_or_create_species_progress(body_pk, "Fonticulua") # tagged, no sample taken yet

        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}ring-active-Bacterium" in shapes
        assert f"{FRAME_PREFIX}ring-active-Fonticulua" not in shapes
        assert f"{FRAME_PREFIX}sample-Fonticulua-0" not in shapes # nothing taken yet -- nothing to draw

    @pytest.mark.overlay('Modern')
    def test_tagged_genus_ring_and_label_still_work_if_re_enabled(self, overlay_mode, store:ExplorerStore, monkeypatch) -> None:
        """
        SHOW_TAGGED_GENUS is off by default (see its docstring), but the code path is kept, not
        deleted, in case this presentation is wanted again -- verify it still actually works.
        """
        import explorer.ui.overlay_frames as overlay_frames
        monkeypatch.setattr(overlay_frames, "SHOW_TAGGED_GENUS", True)

        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=1)
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.get_or_create_species_progress(body_pk, "Fonticulua") # tagged, no sample taken yet

        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        messages = radar.overlay._overlay.messages
        assert shapes[f"{FRAME_PREFIX}ring-active-Bacterium"][0]["color"] == overlay_frames.ACTIVE_RING_COLOR
        assert shapes[f"{FRAME_PREFIX}ring-active-Fonticulua"][0]["color"] == overlay_frames.TAGGED_RING_COLOR
        assert messages[f"{FRAME_PREFIX}label-Fonticulua"][1] == "FON"

    @pytest.mark.overlay('Modern')
    def test_render_clamps_out_of_range_sample_just_past_the_ring_edge_and_hollows_it(self, overlay_mode, store:ExplorerStore) -> None:
        """
        Regression: a sample position outside the display range used to keep drifting further
        from center in screen-space as the player walked away, well past the radar's own edge.
        It should instead clamp to just past the outer ring's edge (same bearing) -- not exactly
        on it, since the ring line itself made a hollow marker hard to see -- and render hollow
        (border only, no fill) to signal "direction only, not an exact fix".
        """
        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=0)
        state.sample_positions["Bacterium"] = [(10.23, 20.0, None)] # ~2007m north -- past the fixed 1500m display range

        radar.render(store, state)

        shape = radar.overlay._overlay.shapes[f"{FRAME_PREFIX}sample-Bacterium-0"]
        border_color, fill_color, sx, sy, w, h = shape[2], shape[3], shape[4], shape[5], shape[6], shape[7]
        assert border_color == SAMPLE_COLOR
        assert fill_color == "" # hollow

        from explorer.ui.overlay_frames import SAMPLE_OUT_OF_RANGE_MARGIN_PX
        cx, cy = sx + w / 2, sy + h / 2
        assert round(math.hypot(cx - CENTER_X, cy - CENTER_Y)) == 150 + SAMPLE_OUT_OF_RANGE_MARGIN_PX

    @pytest.mark.overlay('Modern')
    def test_render_draws_no_active_ring_before_any_sample_is_taken(self, overlay_mode, store:ExplorerStore) -> None:
        """
        A confirmed genus with zero samples taken this visit has no known bearing yet -- only
        the base distance-scale rings show, not a species-specific ring, until sampling begins.
        """
        radar = RadarOverlay(Overlay())
        state = _landed_state(store, samples=0)
        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}ring-1.0" in shapes
        assert f"{FRAME_PREFIX}ring-active-Bacterium" not in shapes
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
    def test_render_draws_base_rings_from_predicted_genus_before_confirmation(self, overlay_mode, store:ExplorerStore) -> None:
        """ Before SAASignalsFound even happens -- a pre-DSS genus prediction (from Scan alone)
        is the fallback when there's no confirmed genus yet, but with no sample taken it's the
        same as any other unstarted genus: only the base distance-scale rings show. """
        radar = RadarOverlay(Overlay())
        state = _flying_state(store)
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.replace_genus_predictions(body_pk, [("Bacterium", None, 0.8)])

        radar.render(store, state)

        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}ring-1.0" in shapes
        assert f"{FRAME_PREFIX}ring-active-Bacterium" not in shapes

    @pytest.mark.overlay('Modern')
    def test_render_is_a_noop_when_no_genus_known_at_all(self, overlay_mode, store:ExplorerStore) -> None:
        """ Flying over a body with no confirmed or predicted genus -- nothing useful to show yet. """
        radar = RadarOverlay(Overlay())
        radar.render(store, _flying_state(store))
        assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.shapes

    @pytest.mark.overlay('Modern')
    def test_render_hides_once_every_genus_is_fully_sampled(self, overlay_mode, store:ExplorerStore) -> None:
        """
        Regression: falling back to a pre-DSS genus prediction whenever there were no *active*
        genera (rather than no genera confirmed AT ALL) meant a body with every genus already
        fully sampled could resurrect a stale prediction and keep the radar showing, instead of
        hiding once there's genuinely nothing left to scan.
        """
        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=0, mark_done=True)
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.replace_genus_predictions(body_pk, [("Bacterium", None, 0.8)]) # stale pre-DSS guess, still on file

        radar.render(store, state)

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
