""" Overlay radar: distance rings, a ring at the current species' minimum sample distance, and a
marker per logged position (real samples vs. codex-tagged waypoints). """
import math
import sqlite3

from config import config # type: ignore

from explorer.utils.debug import Debug
from explorer.utils.overlay import Overlay

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.util import local_offset_m
from explorer.valuation import exobiology_data
from explorer.constants import (
    CFG_PANEL_ENABLED, CFG_OVERLAY_ENABLED, CFG_OVERLAY_RADAR_ENABLED, CFG_OVERLAY_RADAR_SIZE, DEFAULT_OVERLAY_RADAR_SIZE,
)

FRAME_PREFIX:str = "explorerlite-radar-"
PLUGIN_GROUP:str = "EDMC-ExplorerLite"

CENTER_X:int = 640
CENTER_Y:int = 480
RING_SEGMENTS:int = 48 # higher = a rounder-looking circle -- the overlay draws straight segments, no arcs
TTL:int = 8 # generous vs. the ~1/sec dashboard-tick refresh cadence, so a missed/delayed tick doesn't visibly blank the radar
TAG_TRIANGLE_SIZE_PX:int = 5 # vertex-to-center radius for a codex-tagged waypoint's triangle marker

# Disabled: ring/label for a tagged-but-unapproached genus (kept for possible future use).
SHOW_TAGGED_GENUS:bool = False

RING_DISTANCES_M:tuple[int, ...] = (200, 600, 1400) # each double the real-world width of the last
DISPLAY_RANGE_M:float = float(max(RING_DISTANCES_M)) # the "in range" boundary
_RADIUS_FRAC_BOUNDARIES:tuple[float, ...] = (0.0,) + RING_DISTANCES_M

EDGE_DISPLAY_M:float = 1500.0 # radar's true edge -- a bit past the outer ring, margin for out-of-range dots
RING_AREA_FRAC:float = DISPLAY_RANGE_M / EDGE_DISPLAY_M

def _radius_frac(distance_m:float) -> float:
    """ Piecewise-linear 0.0 (0m) to 1.0 (DISPLAY_RANGE_M); each ring segment double the last. """
    if distance_m <= 0:
        return 0.0

    segment_count:int = len(RING_DISTANCES_M)
    for i in range(segment_count):
        lo, hi = _RADIUS_FRAC_BOUNDARIES[i], _RADIUS_FRAC_BOUNDARIES[i + 1]
        if distance_m <= hi:
            return (i + (distance_m - lo) / (hi - lo)) / segment_count

    return 1.0 # beyond the outermost ring -- caller clamps/handles out-of-range separately

def _radius() -> int:
    """ Radar's radius in pixels, configurable. """
    return config.get_int(CFG_OVERLAY_RADAR_SIZE, default=DEFAULT_OVERLAY_RADAR_SIZE)

RING_COLOR:str = "#999999" # neutral grey -- distinct from every CODEX_TAG_COLORS entry below, so it never reads as a species color
ACTIVE_RING_COLOR:str = "#ffaa00" # the current species being sampled this visit
TAGGED_RING_COLOR:str = "#cc66ff" # a genus confirmed but not yet approached this visit -- see SHOW_TAGGED_GENUS
SAMPLE_COLOR:str = "#00aaff" # a real ScanOrganic sample -- never reused below, so a codex-tagged dot is never mistaken for one
PLAYER_COLOR:str = "#ffffff"
LABEL_COLOR:str = "#ffffff"

# Odyssey exobiology variant color names (cross-checked against EDMC-BioScan's name list, not
# its hex values/code) -- a codex tag draws as a hollow triangle in this color, see _draw_samples.
CODEX_TAG_COLORS:dict[str, str] = {
    "Amethyst": "#9966cc", "Aquamarine": "#7fffd4", "Blue": "#3366ff", "Cobalt": "#3355aa",
    "Cyan": "#00e5e5", "Emerald": "#2ecc71", "Gold": "#ffd700", "Green": "#33aa33",
    "Grey": "#aaaaaa", "Indigo": "#6633cc", "Lime": "#bfff00", "Magenta": "#ff33ff",
    "Maroon": "#aa3344", "Mauve": "#aa77aa", "Mulberry": "#993366", "Ocher": "#bb9933",
    "Orange": "#ff8822", "Peach": "#ffaa88", "Red": "#ee3333", "Sage": "#889977",
    "Teal": "#118877", "Turquoise": "#33cccc", "White": "#eeeeee", "Yellow": "#eedd22",
}
DEFAULT_TAG_COLOR:str = "#ff66aa" # an unrecognized color name -- still distinct from SAMPLE_COLOR

def _tag_color(color_name:str|None) -> str:
    return CODEX_TAG_COLORS.get(color_name, DEFAULT_TAG_COLOR) if color_name else DEFAULT_TAG_COLOR

def _triangle_points(cx:float, cy:float, r:float) -> list[dict]:
    """ Equilateral triangle, point-up, vertices r px from center. """
    angles:list[float] = [-math.pi / 2 + 2 * math.pi * i / 3 for i in range(3)]
    points:list[dict] = [{"x": round(cx + r * math.cos(a)), "y": round(cy + r * math.sin(a))} for a in angles]
    return points + [points[0]]

def _genus_label(genus:str) -> str:
    return exobiology_data.genus_code(genus)

def _circle_points(cx:float, cy:float, r:float) -> list[dict]:
    return [
        {"x": round(cx + r * math.cos(2 * math.pi * i / RING_SEGMENTS)), "y": round(cy + r * math.sin(2 * math.pi * i / RING_SEGMENTS))}
        for i in range(RING_SEGMENTS + 1)
    ]

def _rotate_to_heading(east:float, north:float, heading:float) -> tuple[float, float]:
    """ Rotate a world-space (east, north) offset into a heading-up screen frame, where the
    player's current facing direction maps to "forward" (screen up) instead of true north. """
    sin_h, cos_h = math.sin(heading), math.cos(heading)
    forward:float = east * sin_h + north * cos_h
    right:float = east * cos_h - north * sin_h

    return forward, right

class RadarOverlay:
    def __init__(self, overlay:Overlay) -> None:
        self.overlay:Overlay = overlay
        self._group_defined:bool = False
        self._last_skip_reason:str|None = None # dedupe diagnostic logging -- log only on change

    def _log_skip(self, reason:str|None) -> None:
        """ Logs at INFO (no dev-mode needed) only when the reason changes, to avoid
        spamming on every ~1/sec dashboard tick while on-foot. """
        if reason != self._last_skip_reason:
            self._last_skip_reason = reason
            if reason:
                Debug.logger.info(f"Radar overlay not drawing: {reason}")

    def _ensure_group(self) -> None:
        """ Kwargs confirmed against EDMCModernOverlay's real overlay_api.py source. """
        if self._group_defined or not self.overlay.is_modern:
            return
        self._group_defined = self.overlay.define_group(plugin_name=PLUGIN_GROUP, plugin_matching_prefixes=[FRAME_PREFIX],
            plugin_group_name="ExplorerLite Radar", plugin_group_prefixes=[FRAME_PREFIX])

    def render(self, store:ExplorerStore, state:ExplorerState) -> None:
        """ Shown as soon as a body is in view (SupercruiseExit onward, same as the panel's own
        exobiology section) -- not gated behind landed/on-foot, so it's already up guiding you
        in before you commit to landing, not just once you're already down. """
        if not self.overlay.available:
            self._log_skip("no overlay backend detected")
            return

        if not config.get_bool(CFG_PANEL_ENABLED, default=True):
            self._log_skip("panel hidden via the show/hide toggle")
            return

        if not config.get_bool(CFG_OVERLAY_ENABLED, default=True):
            self._log_skip("overlay disabled in EDMC-ExplorerLite settings")
            return

        if not config.get_bool(CFG_OVERLAY_RADAR_ENABLED, default=True):
            self._log_skip("radar disabled in EDMC-ExplorerLite settings")
            return

        if not state.has_lat_long or state.latitude is None or state.longitude is None:
            self._log_skip("no lat/long from Status.json yet")
            return

        if state.cmdr_id is None or state.system_id is None or state.body_id is None:
            self._log_skip(f"missing cmdr/system/body id (cmdr_id={state.cmdr_id}, system_id={state.system_id}, body_id={state.body_id})")
            return

        # Predicted genus only as a fallback when NOTHING is confirmed yet (matches panel.py).
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        all_progress:list[sqlite3.Row] = store.get_species_progress_for_body(body_pk)
        genera:list[str] = self._active_genera(all_progress)

        if not genera and not all_progress:
            predicted:str|None = self._predicted_genus(store.get_genus_predictions_for_body(body_pk))
            genera = [predicted] if predicted else []

        if not genera:
            reason:str = "all genera fully sampled" if all_progress else "no confirmed or predicted genus yet"
            self._log_skip(f"{reason} for body {state.body_name!r} (body_pk={body_pk})")
            return

        self._log_skip(None) # clear -- we're drawing
        self._ensure_group()

        radius_px:int = _radius()
        heading_rad:float = math.radians(state.heading) if state.heading is not None else 0.0
        self._draw_distance_rings(radius_px)

        for genus in genera:
            in_progress:bool = bool(state.sample_positions.get(genus))
            if in_progress:
                # Only the genus actually being sampled gets a ring -- with several genera's
                # samples on screen at once, a ring per genus became illegible.
                if genus == state.current_genus:
                    self._draw_genus_ring(radius_px, genus, ACTIVE_RING_COLOR)
                self._draw_samples(state, genus, radius_px, heading_rad)
                continue

            if SHOW_TAGGED_GENUS:
                self._draw_genus_ring(radius_px, genus, TAGGED_RING_COLOR)
                self._draw_genus_label(radius_px, genus)

        self._draw_player()

    def _active_genera(self, progress:list[sqlite3.Row]) -> list[str]:
        """ Every confirmed genus not yet fully sampled. """
        return [row["genus"] for row in progress if not row["completed_at"]]

    def _predicted_genus(self, predictions:list[sqlite3.Row]) -> str|None:
        """ Best pre-DSS guess (highest confidence, already the query's own ordering). """
        return predictions[0]["genus"] if predictions else None

    def _draw_distance_rings(self, radius_px:int) -> None:
        for distance_m in RING_DISTANCES_M:
            r:float = radius_px * _radius_frac(distance_m) * RING_AREA_FRAC
            self.overlay.send_vect(f"{FRAME_PREFIX}ring-{distance_m}", _circle_points(CENTER_X, CENTER_Y, r), RING_COLOR, ttl=TTL)

    def _draw_genus_ring(self, radius_px:int, genus:str, color:str) -> None:
        min_dist:int|None = exobiology_data.genus_min_distance(genus)
        if not min_dist or min_dist > DISPLAY_RANGE_M:
            return
        r:float = radius_px * _radius_frac(min_dist) * RING_AREA_FRAC
        self.overlay.send_vect(f"{FRAME_PREFIX}ring-active-{genus}", _circle_points(CENTER_X, CENTER_Y, r), color, ttl=TTL)

    def _draw_genus_label(self, radius_px:int, genus:str) -> None:
        """ Only called when SHOW_TAGGED_GENUS is on. """
        min_dist:int|None = exobiology_data.genus_min_distance(genus)
        if not min_dist or min_dist > DISPLAY_RANGE_M:
            return
        r:float = radius_px * _radius_frac(min_dist) * RING_AREA_FRAC
        self.overlay.send_text(f"{FRAME_PREFIX}label-{genus}", _genus_label(genus), LABEL_COLOR, CENTER_X - 10, round(CENTER_Y - r - 14), ttl=TTL)

    def _draw_player(self) -> None:
        self.overlay.send_shape(f"{FRAME_PREFIX}player", "rect", PLAYER_COLOR, PLAYER_COLOR, CENTER_X - 3, CENTER_Y - 3, 6, 6, ttl=TTL)

    def _draw_samples(self, state:ExplorerState, genus:str, radius_px:int, heading:float) -> None:
        """ Bearing (unit direction) and pixel radius (non-linear) computed separately, then combined. """

        positions:list[tuple[float, float, str|None]] = state.sample_positions.get(genus, [])
        if not positions or state.planet_radius is None or state.latitude is None or state.longitude is None:
            return

        for i, (lat, lon, color_name) in enumerate(positions):
            east, north = local_offset_m(state.latitude, state.longitude, lat, lon, state.planet_radius)
            dist:float = math.hypot(east, north)
            in_range:bool = dist <= DISPLAY_RANGE_M
            unit_east, unit_north = (east / dist, north / dist) if dist > 0 else (0.0, 0.0)
            forward, right = _rotate_to_heading(unit_east, unit_north, heading)
            # out of range: midpoint of the reserved outer margin band, same bearing
            pixel_r:float = radius_px * _radius_frac(dist) * RING_AREA_FRAC if in_range else radius_px * (RING_AREA_FRAC + 1.0) / 2
            sx:float = CENTER_X + right * pixel_r
            sy:float = CENTER_Y - forward * pixel_r

            frame_id:str = f"{FRAME_PREFIX}sample-{genus}-{i}"
            if color_name is None:
                # a real sample -- filled/hollow square in the fixed sample color
                fill:str = SAMPLE_COLOR if in_range else "" # hollow once out of range -- position is only a bearing now, not exact
                self.overlay.send_shape(frame_id, "rect", SAMPLE_COLOR, fill, round(sx) - 3, round(sy) - 3, 6, 6, ttl=TTL)
                continue

            # a codex-tagged waypoint -- always-hollow triangle, distinct shape from a real sample
            self.overlay.send_vect(frame_id, _triangle_points(sx, sy, TAG_TRIANGLE_SIZE_PX), _tag_color(color_name), ttl=TTL)
