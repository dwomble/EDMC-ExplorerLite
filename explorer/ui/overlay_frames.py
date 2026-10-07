""" Overlay radar: distance rings, a ring at the current species' minimum sample distance (or, with a
circle-capable overlay, a translucent circle of that distance around its samples and every waypoint), and a
marker per logged position (real samples vs. codex-tagged waypoints). """
import math
import sqlite3
import threading
import time

from config import config # type: ignore

from explorer.utils.debug import Debug
from explorer.utils.overlay import Overlay

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.util import local_offset_m
from explorer.valuation import exobiology_data
from explorer.constants import (
    CFG_PANEL_ENABLED, CFG_OVERLAY_RADAR_ENABLED, CFG_OVERLAY_RADAR_SIZE, DEFAULT_OVERLAY_RADAR_SIZE, CFG_OVERLAY_RADAR_CIRCLES,
    CFG_OVERLAY_RADAR_SWEEP,
)

FRAME_PREFIX:str = "explorerlite-radar-"
PLUGIN_GROUP:str = "EDMC-ExplorerLite"

CENTER_X:int = 640
CENTER_Y:int = 480
RING_THICKNESS_PX:int = 1 # legacy-canvas border width for a native circle ring/dot
DOT_RADIUS_PX:int = 3 # native-circle player marker radius
RING_DOT_SPACING_PX:float = 20.0 # fallback only: target on-screen gap between adjacent dots
RING_DOT_MIN:int = 12
RING_DOT_MAX:int = 40
# A vect shape (any polygon) is outline-only -- the renderer never fills one. Text glyphs are
# the one primitive that's genuinely filled, so a fallback dot is a bullet character.
DOT_GLYPH:str = "•" # bullet
DOT_GLYPH_SIZE:str = "normal" # one of small/normal/large/huge -- no arbitrary pixel size
# send_text's x/y is the text block's top-left, not its center -- these nudge the glyph to
# roughly center on its target point. Guessed, not measured -- tune visually in-game.
DOT_GLYPH_OFFSET_X:int = -3
DOT_GLYPH_OFFSET_Y:int = -6
TTL:int = 8 # generous vs. the ~1/sec dashboard-tick refresh cadence, so a missed/delayed tick doesn't visibly blank the radar
TAG_TRIANGLE_SIZE_PX:int = 5 # vertex-to-center radius for a codex-tagged waypoint's triangle marker
INVISIBLE:str = "#00000000" # fully transparent ARGB -- see _pin_bounds
CIRCLE_FILL_ALPHA:int = 0x40 # ~25% opaque
CIRCLE_BORDER_ALPHA:int = 0xB3 # ~70% opaque
ACTIVE_FILL_ALPHA:int = 0x70 # real samples, stronger than waypoints to stand out
ACTIVE_BORDER_ALPHA:int = 0xFF

SWEEP_PERIOD_S:float = 6.0 # one full turn
SWEEP_INTERVAL_S:float = 1 / 15 # redraw cadence, much faster than render()'s ~1/sec tick
SWEEP_STALE_S:float = float(TTL) # render() only runs when Status.json changes, so match how long the radar's own markers last
SWEEP_TTL:int = 1 # a stopped sweep fades quickly
SWEEP_COLOR:str = "#b333ff88" # translucent green

# Disabled: ring/label for a tagged-but-unapproached genus (kept for possible future use).
SHOW_TAGGED_GENUS:bool = False

RING_DISTANCES_M:tuple[int, ...] = (750, 1500, 2250) # the radar scale is linear, so evenly spaced
DISPLAY_RANGE_M:float = float(max(RING_DISTANCES_M)) # the "in range" boundary

EDGE_DISPLAY_M:float = 2304.0 # radar's true edge -- a bit past the outer ring, margin for out-of-range dots
RING_AREA_FRAC:float = DISPLAY_RANGE_M / EDGE_DISPLAY_M

def _radius_frac(distance_m:float) -> float:
    """ Linear 0.0 (0m) to 1.0 (DISPLAY_RANGE_M), so every circle of a real distance is the same size on screen. """
    return min(max(distance_m, 0.0) / DISPLAY_RANGE_M, 1.0)

def _radius() -> int:
    """ Radar's radius in pixels, configurable. """
    return config.get_int(CFG_OVERLAY_RADAR_SIZE, default=DEFAULT_OVERLAY_RADAR_SIZE)

RING_COLOR:str = "#b2b2b2" # mid grey distance rings
ACTIVE_RING_COLOR:str = "#ffaa00" # the current species being sampled this visit
TAGGED_RING_COLOR:str = "#cc66ff" # a genus confirmed but not yet approached this visit -- see SHOW_TAGGED_GENUS
SAMPLE_COLOR:str = "#00aaff" # fallback for a real sample with no recognized variant color
PLAYER_COLOR:str = "#ffffff"
LABEL_COLOR:str = "#ffffff"

# Odyssey exobiology variant color names
CODEX_TAG_COLORS:dict[str, str] = {
    "Amethyst": "#b67fed", "Aquamarine": "#7fffd4", "Blue": "#658cff", "Cobalt": "#3354a7",
    "Cyan": "#00e5e5", "Emerald": "#2ecc71", "Gold": "#ffd700", "Green": "#14ac14",
    "Grey": "#aaaaaa", "Indigo": "#793cf4", "Lime": "#bfff00", "Magenta": "#ff33ff",
    "Maroon": "#aa3344", "Mauve": "#be53be", "Mulberry": "#B93175", "Ocher": "#cfa528",
    "Orange": "#ff8822", "Peach": "#ffaa88", "Red": "#ee3333", "Rose": "#ff7799", "Sage": "#889977",
    "Teal": "#0C9D87", "Turquoise": "#33cccc", "White": "#eeeeee", "Yellow": "#eedd22",
}
DEFAULT_TAG_COLOR:str = "#ff66aa"

def _tag_color(color_name:str|None) -> str:
    return CODEX_TAG_COLORS.get(color_name, DEFAULT_TAG_COLOR) if color_name else DEFAULT_TAG_COLOR

def _with_alpha(color:str, alpha:int) -> str:
    """ "#rrggbb" to "#aarrggbb" """
    return f"#{alpha:02x}{color[1:]}"

def _sample_color(color_name:str|None) -> str:
    """ Same lookup as _tag_color(), but falls back to SAMPLE_COLOR rather than DEFAULT_TAG_COLOR. """
    return CODEX_TAG_COLORS.get(color_name, SAMPLE_COLOR) if color_name else SAMPLE_COLOR

def _triangle_points(cx:float, cy:float, r:float) -> list[dict]:
    """ Equilateral triangle, point-up, vertices r px from center. """
    angles:list[float] = [-math.pi / 2 + 2 * math.pi * i / 3 for i in range(3)]
    points:list[dict] = [{"x": round(cx + r * math.cos(a)), "y": round(cy + r * math.sin(a))} for a in angles]
    return points + [points[0]]

def _genus_label(genus:str) -> str:
    return exobiology_data.genus_code(genus)

def _ring_dot_count(r:float) -> int:
    """ Scales with circumference """
    if r <= 0:
        return 0
    raw:int = round(2 * math.pi * r / RING_DOT_SPACING_PX)
    return max(RING_DOT_MIN, min(RING_DOT_MAX, raw))

def _ring_dot_positions(cx:float, cy:float, r:float) -> list[tuple[float, float]]:
    """ Dot 0 sits at angle 0 (due "east" in screen space), matching the old polyline's start. """
    count:int = _ring_dot_count(r)
    return [
        (cx + r * math.cos(2 * math.pi * i / count), cy + r * math.sin(2 * math.pi * i / count))
        for i in range(count)
    ]

def _sweep_points(radius:float, t:float) -> list[dict]:
    """ Centre to rim at the sweep's angle for time t: 12 o'clock at t=0, clockwise. """
    angle:float = 2 * math.pi * (t % SWEEP_PERIOD_S) / SWEEP_PERIOD_S
    tip:dict = {"x": round(CENTER_X + radius * math.sin(angle)), "y": round(CENTER_Y - radius * math.cos(angle))}
    return [{"x": CENTER_X, "y": CENTER_Y}, tip]

def _rotate_to_heading(east:float, north:float, heading:float) -> tuple[float, float]:
    """ Rotate a world-space (east, north) offset into a heading-up screen frame """
    sin_h, cos_h = math.sin(heading), math.cos(heading)
    forward:float = east * sin_h + north * cos_h
    right:float = east * cos_h - north * sin_h

    return forward, right

class RadarOverlay:
    def __init__(self, overlay:Overlay) -> None:
        self.overlay:Overlay = overlay
        self._group_defined:bool = False
        self._last_skip_reason:str|None = None # dedupe diagnostic logging -- log only on change
        self._thread:threading.Thread|None = None
        self._halt:threading.Event = threading.Event()
        self._sweep_r:float = 0.0
        self._seen:float = 0.0 # monotonic time of the last render() that actually drew the radar

    def _log_skip(self, reason:str|None) -> None:
        """ Avoid spamming duplicates """
        if reason != self._last_skip_reason:
            self._last_skip_reason = reason
            if reason:
                Debug.logger.info(f"Radar overlay not drawing: {reason}")

    def _ensure_group(self) -> None:
        if self._group_defined or not self.overlay.is_modern:
            return
        self._group_defined = self.overlay.define_group(plugin_name=PLUGIN_GROUP, plugin_matching_prefixes=[FRAME_PREFIX],
            plugin_group_name="ExplorerLite Radar", plugin_group_prefixes=[FRAME_PREFIX])

    def render(self, store:ExplorerStore, state:ExplorerState) -> None:
        if not self.overlay.available:
            self._log_skip("no overlay backend detected")
            return

        if not config.get_bool(CFG_PANEL_ENABLED, default=True):
            self._log_skip("panel hidden via the show/hide toggle")
            return

        if not config.get_bool(CFG_OVERLAY_RADAR_ENABLED, default=True):
            self._log_skip("radar disabled in EDMC-ExplorerLite settings")
            return

        if not state.overlay_relevant:
            self._log_skip("docked, on-foot in a station, or a UI panel has focus")
            return

        if not state.has_lat_long or state.latitude is None or state.longitude is None:
            self._log_skip("no lat/long from Status.json yet")
            return

        if state.cmdr_id is None or state.system_id is None or state.body_id is None:
            self._log_skip(f"missing cmdr/system/body id (cmdr_id={state.cmdr_id}, system_id={state.system_id}, body_id={state.body_id})")
            return

        # Predicted genus only as a fallback when NOTHING is confirmed yet (matches panel.py).
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        all_progress:list[sqlite3.Row] = store.get_species_progress(body_pk)
        genera:list[str] = self._active_genera(all_progress)

        if not genera and not all_progress:
            predicted:str|None = self._predicted_genus(store.get_genus_predictions(body_pk))
            genera = [predicted] if predicted else []

        if not genera:
            reason:str = "all genera fully sampled" if all_progress else "no confirmed or predicted genus yet"
            self._log_skip(f"{reason} for body {state.body_name!r} (body_pk={body_pk})")
            return

        self._log_skip(None) # clear -- we're drawing
        self._ensure_group()

        circles:bool = self.overlay.supports_circle and config.get_bool(CFG_OVERLAY_RADAR_CIRCLES, default=True)
        radius_px:int = _radius()
        heading_rad:float = math.radians(state.heading) if state.heading is not None else 0.0
        began:float = time.monotonic()
        self._pin_bounds(radius_px)
        self._draw_distance_rings(radius_px)

        for genus in genera:
            in_progress:bool = bool(state.sample_positions.get(genus))
            if in_progress:
                # Several rings at once were illegible, so only the genus being sampled gets the ring or sample circles.
                # Waypoints get circles for every genus.
                current:bool = genus == state.current_genus
                if current and not circles:
                    self._draw_genus_ring(radius_px, genus, ACTIVE_RING_COLOR)
                self._draw_samples(state, genus, radius_px, heading_rad, circles, current)
                continue

            if SHOW_TAGGED_GENUS:
                self._draw_genus_ring(radius_px, genus, TAGGED_RING_COLOR)
                self._draw_genus_label(radius_px, genus)

        self._draw_player()

        if time.monotonic() - began > 0.1: Debug.logger.debug(f"Radar render took {time.monotonic() - began:.2f}s")
        if not config.get_bool(CFG_OVERLAY_RADAR_SWEEP, default=False):
            self._seen = 0.0
            return

        self._sweep_r = radius_px * RING_AREA_FRAC
        self._seen = time.monotonic()
        if self._thread is None:
            self._thread = threading.Thread(target=self._sweep_loop, name="ExplorerLite radar sweep", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """ End the sweep thread. """
        self._halt.set()
        if self._thread: self._thread.join(timeout=1)

    def _sweep_loop(self) -> None:
        """ Redraw only the sweep line, at a smooth cadence. """
        last:float = 0.0
        while not self._halt.wait(SWEEP_INTERVAL_S):
            now:float = time.monotonic()
            if now - self._seen > SWEEP_STALE_S:
                last = 0.0
                continue

            if last and now - last > 0.25: Debug.logger.debug(f"Radar sweep gap {now - last:.2f}s")
            last = now
            self.overlay.send_vect(f"{FRAME_PREFIX}sweep", _sweep_points(self._sweep_r, now), SWEEP_COLOR, ttl=SWEEP_TTL)

    def _active_genera(self, progress:list[sqlite3.Row]) -> list[str]:
        """ Every confirmed genus not yet fully sampled. """
        return list(dict.fromkeys(row["genus"] for row in progress if not row["completed_at"]))

    def _predicted_genus(self, predictions:list[sqlite3.Row]) -> str|None:
        """ Best pre-DSS guess (highest confidence, already the query's own ordering). """
        return predictions[0]["genus"] if predictions else None

    def _draw_ring(self, frame_id:str, r:float, color:str) -> None:
        """ A native circle when the overlay supports it, else the dot-glyph fallback (see module docstring). """
        if r <= 0:
            return
        if self.overlay.supports_circle:
            self.overlay.send_circle(frame_id, color, "none", CENTER_X, CENTER_Y, round(r), RING_THICKNESS_PX, ttl=TTL)
            return
        for i, (x, y) in enumerate(_ring_dot_positions(CENTER_X, CENTER_Y, r)):
            self.overlay.send_text(f"{frame_id}-{i}", DOT_GLYPH, color,
                                   round(x) + DOT_GLYPH_OFFSET_X, round(y) + DOT_GLYPH_OFFSET_Y, ttl=TTL, size=DOT_GLYPH_SIZE)

    def _pin_bounds(self, radius_px:int) -> None:
        """ Two invisible markers spanning the radar's full extent, stopping it drifting as visible markers change. """
        self.overlay.send_text(f"{FRAME_PREFIX}pin-nw", " ", INVISIBLE, CENTER_X - radius_px, CENTER_Y - radius_px, ttl=TTL)
        self.overlay.send_text(f"{FRAME_PREFIX}pin-se", " ", INVISIBLE, CENTER_X + radius_px, CENTER_Y + radius_px, ttl=TTL)

    def _draw_distance_rings(self, radius_px:int) -> None:
        for distance_m in RING_DISTANCES_M:
            r:float = radius_px * _radius_frac(distance_m) * RING_AREA_FRAC
            self._draw_ring(f"{FRAME_PREFIX}ring-{distance_m}", r, RING_COLOR)

    def _draw_genus_ring(self, radius_px:int, genus:str, color:str) -> None:
        min_dist:int|None = exobiology_data.genus_min_distance(genus)
        if not min_dist or min_dist > DISPLAY_RANGE_M:
            return
        r:float = radius_px * _radius_frac(min_dist) * RING_AREA_FRAC
        self._draw_ring(f"{FRAME_PREFIX}ring-active-{genus}", r, color)

    def _draw_genus_label(self, radius_px:int, genus:str) -> None:
        """ Only called when SHOW_TAGGED_GENUS is on. """
        min_dist:int|None = exobiology_data.genus_min_distance(genus)
        if not min_dist or min_dist > DISPLAY_RANGE_M:
            return
        r:float = radius_px * _radius_frac(min_dist) * RING_AREA_FRAC
        self.overlay.send_text(f"{FRAME_PREFIX}label-{genus}", _genus_label(genus), LABEL_COLOR, CENTER_X - 10,
                               round(CENTER_Y - r - 14), ttl=TTL)

    def _draw_player(self) -> None:
        frame_id:str = f"{FRAME_PREFIX}player"
        if self.overlay.supports_circle:
            self.overlay.send_circle(frame_id, PLAYER_COLOR, PLAYER_COLOR, CENTER_X, CENTER_Y, DOT_RADIUS_PX, RING_THICKNESS_PX, ttl=TTL)
            return
        self.overlay.send_text(
            frame_id, DOT_GLYPH, PLAYER_COLOR,
            CENTER_X + DOT_GLYPH_OFFSET_X, CENTER_Y + DOT_GLYPH_OFFSET_Y, ttl=TTL, size=DOT_GLYPH_SIZE,
        )

    def _draw_samples(self, state:ExplorerState, genus:str, radius_px:int, heading:float, circles:bool = False, current:bool = False) -> None:
        """ Bearing (unit direction) and pixel radius (non-linear) computed separately, then combined. """

        positions:list[tuple[float, float, str|None, bool]] = state.sample_positions.get(genus, [])
        if not positions or state.planet_radius is None or state.latitude is None or state.longitude is None:
            return

        min_dist:int = (exobiology_data.genus_min_distance(genus) or 0) if circles else 0
        px_per_m:float = radius_px * RING_AREA_FRAC / DISPLAY_RANGE_M
        for i, (lat, lon, color_name, is_tag) in enumerate(positions):
            east, north = local_offset_m(state.latitude, state.longitude, lat, lon, state.planet_radius)
            dist:float = math.hypot(east, north)
            in_range:bool = dist <= DISPLAY_RANGE_M
            unit_east, unit_north = (east / dist, north / dist) if dist > 0 else (0.0, 0.0)
            forward, right = _rotate_to_heading(unit_east, unit_north, heading)
            # out of range: midpoint of the reserved outer margin band, same bearing
            pixel_r:float = radius_px * _radius_frac(dist) * RING_AREA_FRAC if in_range else radius_px * (RING_AREA_FRAC + 1.0) / 2
            sx:float = CENTER_X + right * pixel_r
            sy:float = CENTER_Y - forward * pixel_r

            if min_dist and in_range and (is_tag or current):
                color:str = _tag_color(color_name) if is_tag else _sample_color(color_name)
                border_alpha:int = CIRCLE_BORDER_ALPHA if is_tag else ACTIVE_BORDER_ALPHA
                fill_alpha:int = CIRCLE_FILL_ALPHA if is_tag else ACTIVE_FILL_ALPHA
                true_r:float = min_dist * px_per_m
                # clamped inside the pinned bounds, else the group's bounding box shifts and the radar jumps
                circle_r:int = round(min(true_r, radius_px - abs(sx - CENTER_X), radius_px - abs(sy - CENTER_Y)))
                self.overlay.send_circle(f"{FRAME_PREFIX}circle-{genus}-{i}", _with_alpha(color, border_alpha), _with_alpha(color, fill_alpha),
                                         round(sx), round(sy), circle_r, RING_THICKNESS_PX, ttl=TTL)

            frame_id:str = f"{FRAME_PREFIX}sample-{genus}-{i}"
            if not is_tag:
                # a real sample -- square, its variant color
                border:str = _sample_color(color_name)
                fill:str = border if in_range else "" # hollow once out of range -- position is only a bearing now, not exact
                self.overlay.send_shape(frame_id, "rect", border, fill, round(sx) - 3, round(sy) - 3, 6, 6, ttl=TTL)
                continue

            # a codex-tagged waypoint -- always-hollow triangle, distinct shape from a real sample
            self.overlay.send_vect(frame_id, _triangle_points(sx, sy, TAG_TRIANGLE_SIZE_PX), _tag_color(color_name), ttl=TTL)
