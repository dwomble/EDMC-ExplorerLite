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
from explorer.ui.overlay_frames import _radius_frac, _ring_dot_count, RING_DOT_MIN, RING_DOT_MAX, DOT_GLYPH, DOT_GLYPH_SIZE, RING_THICKNESS_PX, DOT_RADIUS_PX, PLAYER_COLOR, CODEX_TAG_COLORS, RING_AREA_FRAC, DOT_GLYPH_OFFSET_X, RING_DISTANCES_M, DISPLAY_RANGE_M
from explorer.constants import DEFAULT_OVERLAY_RADAR_SIZE, CFG_OVERLAY_RADAR_SIZE, CFG_OVERLAY_RADAR_ENABLED, CFG_PANEL_ENABLED, CFG_OVERLAY_RADAR_CIRCLES
from explorer.ui.overlay_frames import CIRCLE_FILL_ALPHA, CIRCLE_BORDER_ALPHA, OTHER_FILL_ALPHA, OTHER_BORDER_ALPHA, CURRENT_CIRCLE_COLOR, RING_COLOR
from explorer.util import local_offset_m
from explorer.valuation import exobiology_data
import explorer.ui.overlay_frames as overlay_frames

OUTER:int = RING_DISTANCES_M[-1] # the outermost distance ring, in meters

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

class TestRadiusFrac:
    """ The radar's distance scale (_radius_frac) is linear from 0m at dead center to DISPLAY_RANGE_M
    at the outermost ring, so a circle of a real distance is a true circle on screen. """

    def test_zero_and_the_outer_ring_land_on_the_ends(self) -> None:
        assert _radius_frac(0) == 0.0
        assert _radius_frac(DISPLAY_RANGE_M) == 1.0

    def test_scale_is_linear(self) -> None:
        assert _radius_frac(DISPLAY_RANGE_M / 4) == pytest.approx(0.25)
        assert _radius_frac(DISPLAY_RANGE_M / 2) == pytest.approx(0.5)

    def test_smallest_known_genus_min_distance_is_visible(self) -> None:
        """ 100m (Amphora Plant/Anemone/etc's minimum) must not collapse to a point. """
        assert _radius_frac(100) * 150 * RING_AREA_FRAC > 3 # pixels, at the default radar size

    def test_largest_known_genus_min_distance_stays_within_the_outer_ring(self) -> None:
        """ Electricae's 1000m, the largest across all known genera, must land inside the outer ring. """
        assert 0.0 < _radius_frac(1000) < 1.0

    def test_beyond_the_outer_ring_clamps_to_one(self) -> None:
        assert _radius_frac(DISPLAY_RANGE_M * 2) == 1.0

class TestRingDotCount:
    """ A ring is drawn as individually-sent dot markers, not a connected polyline (the overlay
    protocol has no native circle shape -- see explorer team's own research). Dot count scales
    with circumference so spacing stays roughly constant from the smallest to largest ring. """

    def test_zero_radius_has_no_dots(self) -> None:
        assert _ring_dot_count(0) == 0

    def test_tiny_ring_clamps_to_the_minimum(self) -> None:
        assert _ring_dot_count(5) == RING_DOT_MIN

    def test_huge_ring_clamps_to_the_maximum(self) -> None:
        assert _ring_dot_count(10_000) == RING_DOT_MAX

    def test_mid_sized_ring_scales_with_circumference(self) -> None:
        count:int = _ring_dot_count(60)
        assert RING_DOT_MIN < count < RING_DOT_MAX

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
        state.sample_positions[genus] = [(10.0 + i * 0.0001, 20.0, None, False) for i in range(samples)]
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

class TestRadarSampleCircles:
    """ With a circle-capable overlay, translucent circles of the species' minimum sample distance
    surround the current genus's samples and codex-tagged waypoints, replacing the central ring. """

    def _render(self, store:ExplorerStore, state:ExplorerState) -> dict:
        radar = RadarOverlay(Overlay())
        radar.overlay.supports_circle = True
        radar.render(store, state)
        return radar.overlay._overlay.shapes

    @pytest.mark.overlay('Modern')
    def test_circles_replace_central_ring(self, overlay_mode, store:ExplorerStore) -> None:
        state = _landed_state(store, samples=1)
        state.sample_positions["Bacterium"].append((10.0002, 20.0, "Lime", True))

        shapes = self._render(store, state)

        assert f"{FRAME_PREFIX}ring-active-Bacterium" not in shapes
        _, shape, sample = shapes[f"{FRAME_PREFIX}circle-Bacterium-0"]
        assert shape == "circle"
        assert sample["color"] == f"#{CIRCLE_BORDER_ALPHA:02x}{CURRENT_CIRCLE_COLOR[1:]}"
        assert sample["fill"] == f"#{CIRCLE_FILL_ALPHA:02x}{CURRENT_CIRCLE_COLOR[1:]}"
        _, _, tag = shapes[f"{FRAME_PREFIX}circle-Bacterium-1"] # the current genus's waypoint is white too
        assert tag["color"] == sample["color"]

    @pytest.mark.overlay('Modern')
    def test_radius_is_to_scale_at_any_distance(self, overlay_mode, store:ExplorerStore) -> None:
        state = _landed_state(store, samples=0)
        state.current_genus = "Bacterium"
        state.sample_positions["Bacterium"] = [(10.0, 20.0, None, False), (10.045, 20.0, None, False)] # at the player, then ~390m away
        shapes = self._render(store, state)

        min_dist:int = exobiology_data.genus_min_distance("Bacterium") or 0
        expected:int = round(min_dist * DEFAULT_OVERLAY_RADAR_SIZE * RING_AREA_FRAC / DISPLAY_RANGE_M)
        assert shapes[f"{FRAME_PREFIX}circle-Bacterium-0"][2]["radius"] == expected
        assert shapes[f"{FRAME_PREFIX}circle-Bacterium-1"][2]["radius"] == expected

    @pytest.mark.overlay('Modern')
    def test_out_of_range_sample_has_no_circle(self, overlay_mode, store:ExplorerStore) -> None:
        state = _landed_state(store, samples=0)
        state.current_genus = "Bacterium"
        state.sample_positions["Bacterium"] = [(10.4, 20.0, None, False)] # ~3.5km, past the outer ring

        shapes = self._render(store, state)

        assert f"{FRAME_PREFIX}circle-Bacterium-0" not in shapes
        assert f"{FRAME_PREFIX}sample-Bacterium-0" in shapes

    @pytest.mark.overlay('Modern')
    def test_other_genus_samples_get_no_circle(self, overlay_mode, store:ExplorerStore) -> None:
        state = _landed_state(store, genus="Bacterium", samples=1)
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.get_or_create_species_progress(body_pk, "Fungoida")
        state.sample_positions["Fungoida"] = [(10.0003, 20.0, None, False)]

        shapes = self._render(store, state)

        assert f"{FRAME_PREFIX}circle-Bacterium-0" in shapes
        assert f"{FRAME_PREFIX}circle-Fungoida-0" not in shapes
        assert f"{FRAME_PREFIX}sample-Fungoida-0" in shapes

    @pytest.mark.overlay('Modern')
    def test_other_genus_waypoints_get_their_own_circle(self, overlay_mode, store:ExplorerStore) -> None:
        state = _landed_state(store, genus="Bacterium", samples=1)
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.get_or_create_species_progress(body_pk, "Fungoida")
        state.sample_positions["Fungoida"] = [(10.0003, 20.0, "Lime", True)]

        shapes = self._render(store, state)

        _, _, kwargs = shapes[f"{FRAME_PREFIX}circle-Fungoida-0"]
        fungoida:int = exobiology_data.genus_min_distance("Fungoida") or 0
        assert kwargs["radius"] == round(fungoida * DEFAULT_OVERLAY_RADAR_SIZE * RING_AREA_FRAC / DISPLAY_RANGE_M)
        assert kwargs["color"] == f"#{OTHER_BORDER_ALPHA:02x}{CODEX_TAG_COLORS['Lime'][1:]}" # species color, more transparent
        assert kwargs["fill"] == f"#{OTHER_FILL_ALPHA:02x}{CODEX_TAG_COLORS['Lime'][1:]}"

    @pytest.mark.overlay('Modern')
    def test_pref_off_keeps_central_ring(self, overlay_mode, harness:TestHarness, store:ExplorerStore) -> None:
        harness.config.set(CFG_OVERLAY_RADAR_CIRCLES, False)
        try:
            shapes = self._render(store, _landed_state(store, samples=1))
        finally:
            harness.config.set(CFG_OVERLAY_RADAR_CIRCLES, True)

        assert f"{FRAME_PREFIX}ring-active-Bacterium" in shapes
        assert f"{FRAME_PREFIX}circle-Bacterium-0" not in shapes

    @pytest.mark.overlay('Modern')
    def test_no_circle_support_keeps_glyph_ring(self, overlay_mode, store:ExplorerStore) -> None:
        radar = RadarOverlay(Overlay())
        radar.render(store, _landed_state(store, samples=1))

        assert any(k.startswith(f"{FRAME_PREFIX}ring-active-Bacterium-") for k in radar.overlay._overlay.messages)
        assert f"{FRAME_PREFIX}circle-Bacterium-0" not in radar.overlay._overlay.shapes

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

        messages = radar.overlay._overlay.messages
        assert f"{FRAME_PREFIX}ring-{OUTER}-0" in messages
        assert f"{FRAME_PREFIX}ring-active-Bacterium-0" in messages # Bacterium's 500m min-distance fits within the fixed 2000m display range
        assert f"{FRAME_PREFIX}player" in messages
        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}sample-Bacterium-0" in shapes
        assert f"{FRAME_PREFIX}sample-Bacterium-1" in shapes

    @pytest.mark.overlay('Modern')
    def test_pin_bounds_stay_fixed(self, overlay_mode, store:ExplorerStore) -> None:
        """ The pin markers stay at a fixed position regardless of sample count. """
        r:int = DEFAULT_OVERLAY_RADAR_SIZE

        radar = RadarOverlay(Overlay())
        radar.render(store, _landed_state(store, samples=1))
        messages = radar.overlay._overlay.messages
        nw_first = tuple(messages[f"{FRAME_PREFIX}pin-nw"][3:5])
        se_first = tuple(messages[f"{FRAME_PREFIX}pin-se"][3:5])

        radar.render(store, _landed_state(store, samples=20))
        messages = radar.overlay._overlay.messages
        nw_second = tuple(messages[f"{FRAME_PREFIX}pin-nw"][3:5])
        se_second = tuple(messages[f"{FRAME_PREFIX}pin-se"][3:5])

        assert nw_first == nw_second == (CENTER_X - r, CENTER_Y - r)
        assert se_first == se_second == (CENTER_X + r, CENTER_Y + r)

    @pytest.mark.overlay('Modern')
    def test_ring_is_drawn_as_multiple_small_dot_glyphs(self, overlay_mode, store:ExplorerStore) -> None:
        """ Fallback path (Overlay.supports_circle is False, the mock's default): each dot is
        its own small text-glyph message -- not one big connected polyline (see
        RING_DOT_MIN/_ring_dot_count's module docstring for why). A vect shape is outline-only,
        so a filled dot has to be a real glyph instead (see DOT_GLYPH). """

        radar = RadarOverlay(Overlay())
        radar.render(store, _landed_state(store, samples=0))

        messages = radar.overlay._overlay.messages
        assert f"{FRAME_PREFIX}ring-{OUTER}-1" in messages # more than just dot 0 -- an actual ring, not a single point
        assert f"{FRAME_PREFIX}ring-{OUTER}-{RING_DOT_MIN - 1}" in messages

        _, text, _, _, _, kwargs = messages[f"{FRAME_PREFIX}ring-{OUTER}-0"]
        assert text == DOT_GLYPH
        assert kwargs["size"] == DOT_GLYPH_SIZE

    @pytest.mark.overlay('Modern')
    def test_ring_draws_as_one_native_circle_when_the_backend_supports_it(self, overlay_mode, store:ExplorerStore) -> None:
        """ Pre-release EDMCModernOverlay send_shape("circle", ...) support, detected via
        Overlay.supports_circle -- one real circle, not the multi-dot fallback above. """

        radar = RadarOverlay(Overlay())
        radar.overlay.supports_circle = True
        radar.render(store, _landed_state(store, samples=0))

        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}ring-{OUTER}-0" not in shapes # no per-dot fallback ids
        _, shape, kwargs = shapes[f"{FRAME_PREFIX}ring-{OUTER}"]
        assert shape == "circle"
        assert kwargs["fill"] == "none" # a ring outlines a distance, it doesn't cover the view
        assert kwargs["thickness"] == RING_THICKNESS_PX
        assert kwargs["x"] == CENTER_X and kwargs["y"] == CENTER_Y
        assert kwargs["color"] == RING_COLOR

    @pytest.mark.overlay('Modern')
    def test_player_draws_as_a_filled_native_circle_when_the_backend_supports_it(self, overlay_mode, store:ExplorerStore) -> None:

        radar = RadarOverlay(Overlay())
        radar.overlay.supports_circle = True
        radar.render(store, _landed_state(store, samples=0))

        shapes = radar.overlay._overlay.shapes
        _, shape, kwargs = shapes[f"{FRAME_PREFIX}player"]
        assert shape == "circle"
        assert kwargs["radius"] == DOT_RADIUS_PX
        assert kwargs["fill"] == PLAYER_COLOR # solid, unlike a ring -- it's a single point, not a boundary
        assert kwargs["x"] == CENTER_X and kwargs["y"] == CENTER_Y

    @pytest.mark.overlay('Modern')
    def test_codex_tagged_sample_is_a_triangle_in_its_variant_color(self, overlay_mode, store:ExplorerStore) -> None:
        """
        A CodexEntry waypoint tag used to look identical to a real sample -- both drawn as the
        same filled square in SAMPLE_COLOR. A tag now draws as a hollow TRIANGLE in the game's
        own reported variant color (state.py's sample_positions third element) instead --
        shape, not just color, is what keeps it from ever being mistaken for a real sample.
        """

        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=1) # a real sample -- (lat, lon, None, False)
        state.sample_positions["Bacterium"].append((10.0002, 20.0, "Lime", True)) # a codex-tagged waypoint

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
        state.sample_positions["Bacterium"] = [(10.01, 20.0, None, False)] # ~87m due north of the player
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
        state.sample_positions["Fonticulua"] = [(10.0001, 20.0, None, False)]
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.get_or_create_species_progress(body_pk, "Fonticulua")

        radar.render(store, state)

        messages = radar.overlay._overlay.messages
        assert f"{FRAME_PREFIX}ring-active-Bacterium-0" in messages # current_genus -- gets the ring
        assert f"{FRAME_PREFIX}ring-active-Fonticulua-0" not in messages # in progress too, but not current -- no ring
        shapes = radar.overlay._overlay.shapes
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

        messages = radar.overlay._overlay.messages
        assert f"{FRAME_PREFIX}ring-active-Bacterium-0" in messages
        assert f"{FRAME_PREFIX}ring-active-Fonticulua-0" not in messages
        shapes = radar.overlay._overlay.shapes
        assert f"{FRAME_PREFIX}sample-Fonticulua-0" not in shapes # nothing taken yet -- nothing to draw

    @pytest.mark.overlay('Modern')
    def test_tagged_genus_ring_and_label_still_work_if_re_enabled(self, overlay_mode, store:ExplorerStore, monkeypatch) -> None:
        """
        SHOW_TAGGED_GENUS is off by default (see its docstring), but the code path is kept, not
        deleted, in case this presentation is wanted again -- verify it still actually works.
        """
        monkeypatch.setattr(overlay_frames, "SHOW_TAGGED_GENUS", True)

        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=1)
        assert state.cmdr_id is not None and state.system_id is not None and state.body_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        store.get_or_create_species_progress(body_pk, "Fonticulua") # tagged, no sample taken yet

        radar.render(store, state)

        messages = radar.overlay._overlay.messages
        assert messages[f"{FRAME_PREFIX}ring-active-Bacterium-0"][2] == overlay_frames.ACTIVE_RING_COLOR
        assert messages[f"{FRAME_PREFIX}ring-active-Fonticulua-0"][2] == overlay_frames.TAGGED_RING_COLOR
        assert messages[f"{FRAME_PREFIX}label-Fonticulua"][1] == "FON"

    @pytest.mark.overlay('Modern')
    def test_render_clamps_out_of_range_sample_just_past_the_ring_edge_and_hollows_it(self, overlay_mode, store:ExplorerStore) -> None:
        """
        Regression: a sample position outside the display range used to keep drifting further
        from center in screen-space as the player walked away, well past the radar's own edge.
        It should instead clamp to the midpoint of the reserved outer margin band (same bearing,
        between the outermost ring and the radar's true edge) -- clear of the ring line, and
        never past the configured radar size either -- and render hollow (border only, no fill)
        to signal "direction only, not an exact fix".
        """

        radar = RadarOverlay(Overlay())
        state = _landed_state(store, genus="Bacterium", samples=0)
        state.sample_positions["Bacterium"] = [(10.4, 20.0, None, False)] # ~3490m north -- past the fixed 2000m display range

        radar.render(store, state)

        shape = radar.overlay._overlay.shapes[f"{FRAME_PREFIX}sample-Bacterium-0"]
        border_color, fill_color, sx, sy, w, h = shape[2], shape[3], shape[4], shape[5], shape[6], shape[7]
        assert border_color == SAMPLE_COLOR
        assert fill_color == "" # hollow

        cx, cy = sx + w / 2, sy + h / 2
        expected_r = 150 * (RING_AREA_FRAC + 1.0) / 2
        assert math.hypot(cx - CENTER_X, cy - CENTER_Y) == pytest.approx(expected_r, abs=1) # positions are rounded to whole pixels

    @pytest.mark.overlay('Modern')
    def test_render_draws_no_active_ring_before_any_sample_is_taken(self, overlay_mode, store:ExplorerStore) -> None:
        """
        A confirmed genus with zero samples taken this visit has no known bearing yet -- only
        the base distance-scale rings show, not a species-specific ring, until sampling begins.
        """
        radar = RadarOverlay(Overlay())
        state = _landed_state(store, samples=0)
        radar.render(store, state)

        messages = radar.overlay._overlay.messages
        assert f"{FRAME_PREFIX}ring-{OUTER}-0" in messages
        assert f"{FRAME_PREFIX}ring-active-Bacterium-0" not in messages
        assert f"{FRAME_PREFIX}player" in messages

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

        messages = radar.overlay._overlay.messages
        assert f"{FRAME_PREFIX}ring-{OUTER}-0" in messages
        assert f"{FRAME_PREFIX}player" in messages

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

        messages = radar.overlay._overlay.messages
        assert f"{FRAME_PREFIX}ring-{OUTER}-0" in messages
        assert f"{FRAME_PREFIX}ring-active-Bacterium-0" not in messages

    @pytest.mark.overlay('Modern')
    def test_render_is_a_noop_when_no_genus_known_at_all(self, overlay_mode, store:ExplorerStore) -> None:
        """ Flying over a body with no confirmed or predicted genus -- nothing useful to show yet. """
        radar = RadarOverlay(Overlay())
        radar.render(store, _flying_state(store))
        assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.messages

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

        assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.messages

    @pytest.mark.overlay('Modern')
    def test_render_is_a_noop_without_lat_long(self, overlay_mode, store:ExplorerStore) -> None:
        radar = RadarOverlay(Overlay())
        state = _landed_state(store)
        state.has_lat_long = False
        radar.render(store, state)
        assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.messages

    @pytest.mark.overlay('Modern')
    def test_render_is_a_noop_while_docked(self, overlay_mode, store:ExplorerStore) -> None:
        radar = RadarOverlay(Overlay())
        state = _landed_state(store)
        state.docked = True
        radar.render(store, state)
        assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.messages

    @pytest.mark.overlay('Modern')
    def test_render_is_a_noop_on_foot_in_a_station(self, overlay_mode, store:ExplorerStore) -> None:
        radar = RadarOverlay(Overlay())
        state = _landed_state(store)
        state.on_foot_in_station = True
        radar.render(store, state)
        assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.messages

    @pytest.mark.overlay('Modern')
    def test_render_is_a_noop_while_a_ui_panel_has_focus(self, overlay_mode, store:ExplorerStore) -> None:
        """ e.g. galaxy map / system map open in the ship -- GuiFocus != 0. """
        from edmc_data import GuiFocusGalaxyMap # type: ignore
        radar = RadarOverlay(Overlay())
        state = _landed_state(store)
        state.gui_focus = GuiFocusGalaxyMap
        radar.render(store, state)
        assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.messages

    @pytest.mark.overlay('Modern')
    def test_render_respects_configured_radar_size(self, overlay_mode, harness:TestHarness, store:ExplorerStore) -> None:
        harness.config.set(CFG_OVERLAY_RADAR_SIZE, 300)
        try:
            radar = RadarOverlay(Overlay())
            state = _landed_state(store, samples=0)
            radar.render(store, state)

            _, _, _, x, _, _ = radar.overlay._overlay.messages[f"{FRAME_PREFIX}ring-{OUTER}-0"]
            # dot 0's glyph position is nudged by DOT_GLYPH_OFFSET_X off the actual ring point --
            # the outermost ring sits at RING_AREA_FRAC of the configured size, not the full
            # radius -- the remaining margin is reserved for out-of-range dots (see module docstring)
            assert x - DOT_GLYPH_OFFSET_X - CENTER_X == pytest.approx(300 * RING_AREA_FRAC, abs=1)
        finally:
            harness.config.set(CFG_OVERLAY_RADAR_SIZE, 150)

    @pytest.mark.overlay('Modern')
    def test_render_respects_radar_disabled_config(self, overlay_mode, harness:TestHarness, store:ExplorerStore) -> None:
        harness.config.set(CFG_OVERLAY_RADAR_ENABLED, False)
        try:
            radar = RadarOverlay(Overlay())
            radar.render(store, _landed_state(store))
            assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.messages
        finally:
            harness.config.set(CFG_OVERLAY_RADAR_ENABLED, True)

    @pytest.mark.overlay('Modern')
    def test_render_respects_panel_hidden_via_show_hide_toggle(self, overlay_mode, harness:TestHarness, store:ExplorerStore) -> None:
        harness.config.set(CFG_PANEL_ENABLED, False)
        try:
            radar = RadarOverlay(Overlay())
            radar.render(store, _landed_state(store))
            assert f"{FRAME_PREFIX}player" not in radar.overlay._overlay.messages
        finally:
            harness.config.set(CFG_PANEL_ENABLED, True)

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
