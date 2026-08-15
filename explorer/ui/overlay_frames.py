"""
Overlay radar: distance rings on a fixed real-world scale, a highlighted ring at the CURRENT
species' required minimum sample distance, and a marker per logged position -- for every
in-progress genus, not just the current one. A real ScanOrganic sample draws a filled/hollow
SQUARE in the fixed SAMPLE_COLOR; a CodexEntry waypoint tag draws a hollow TRIANGLE in the
game's own reported variant color instead (see CODEX_TAG_COLORS) -- shape, not just color, is
what keeps a passive "spotted it" tag from ever being mistaken for a real sample, which also
means a tag's true color is always safe to use even when it's a blue/cyan one. Visible from
SupercruiseExit onward (flying over the surface, not just on-foot) whenever a confirmed genus
has at least one sample taken this visit -- a genus that's merely been tagged via
SAASignalsFound but not yet approached this visit draws nothing by default (see
SHOW_TAGGED_GENUS): there's no known bearing to it yet, only a distance, and showing a
differently-colored ring + label for it either conveyed no real information or (once heading-up
was added) misleadingly suggested a direction, since the label's fixed screen anchor always
coincided with "straight ahead". Only ONE ring is ever drawn at a time -- state.current_genus,
the genus of the most recent real ScanOrganic sample -- since several genera's rings on screen
simultaneously became illegible; markers for every in-progress genus still show regardless.
Built on the generic utils/overlay.py wrapper -- this module supplies EDMC-ExplorerLite's own
frame names, positions, and colors, which is deliberately NOT part of the shared library (see
PluginLib's overlay.py docstring).

Heading-up, not north-up: the player's current facing direction always maps to screen "up", so
the whole radar (rings excepted -- concentric circles look the same either way -- but sample
markers) rotates as you turn, rather than a separate tick line showing facing against a fixed
north-up frame. Sample markers are positioned relative to the player's CURRENT position and
heading each call, so they correctly drift/rotate as the player walks/turns, same as a real
heading-up radar.

The 4 green distance rings sit on a fixed DISPLAY_RANGE_M scale (1.5x the largest known genus
minimum sample distance, currently Electricae's 1000m -- see exobiology_data.GENUS_MIN_DISTANCE_M),
not a per-genus adaptive scale, so the same ring always means the same real-world distance
regardless of which species is being tracked -- a genuine fixed reference, not a moving target.

No explicit "clear" -- every shape is sent with a short TTL and simply stops being refreshed
(and expires on the overlay) once render() stops being called for this genus/body, which
happens naturally once the panel/dispatch flags say the overlay is no longer relevant.
"""
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
    CFG_OVERLAY_ENABLED, CFG_OVERLAY_RADAR_ENABLED, CFG_OVERLAY_RADAR_SIZE, DEFAULT_OVERLAY_RADAR_SIZE,
)

FRAME_PREFIX:str = "explorerlite-radar-"
PLUGIN_GROUP:str = "EDMC-ExplorerLite"

CENTER_X:int = 640
CENTER_Y:int = 480
RING_SEGMENTS:int = 24
TTL:int = 8 # generous vs. the ~1/sec dashboard-tick refresh cadence, so a missed/delayed tick doesn't visibly blank the radar
SAMPLE_OUT_OF_RANGE_MARGIN_PX:int = 12 # how far past the outer ring an out-of-range sample sits, clear of the ring line
TAG_TRIANGLE_SIZE_PX:int = 5 # vertex-to-center radius for a codex-tagged waypoint's triangle marker

# Off by default (2026-08): a ring + label for a confirmed-but-not-yet-approached genus turned
# out to convey no useful info before heading-up, and misleadingly suggested a direction after
# it. Kept (not deleted) in case a future presentation of "tagged genus" info is wanted again.
SHOW_TAGGED_GENUS:bool = False

# Fixed real-world scale for the 4 green rings -- 1.5x the largest known genus minimum sample
# distance, so the ring positions mean the same thing regardless of which species is on screen.
DISPLAY_RANGE_M:float = 1.5 * max(exobiology_data.GENUS_MIN_DISTANCE_M.values())

def _radius_px() -> int:
    return config.get_int(CFG_OVERLAY_RADAR_SIZE, default=DEFAULT_OVERLAY_RADAR_SIZE)

RING_COLOR:str = "#00ff00"
ACTIVE_RING_COLOR:str = "#ffaa00" # the current species being sampled this visit
TAGGED_RING_COLOR:str = "#cc66ff" # a genus confirmed but not yet approached this visit -- see SHOW_TAGGED_GENUS
SAMPLE_COLOR:str = "#00aaff" # a real ScanOrganic sample -- never reused below, so a codex-tagged dot is never mistaken for one
PLAYER_COLOR:str = "#ffffff"
LABEL_COLOR:str = "#ffffff"

# CodexEntry-tagged waypoints are drawn as a hollow TRIANGLE in the game's own reported variant
# color, vs. a real sample's filled/hollow SQUARE in the fixed SAMPLE_COLOR -- shape (not just
# color) tells them apart, so a tag can safely use its true reported color, including blue/cyan
# ones, without ever being mistaken for a real sample. Names are the full known set of Odyssey
# exobiology variant colors (cross-checked against EDMC-BioScan's own color-name list, not its
# hex values or code -- these hex values are our own).
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
    """ First 3 letters, uppercased -- confirmed unique across all 21 known genera in
    exobiology_data.py, so it's enough to tell simultaneously-drawn genera apart at a glance. """
    return genus[:3].upper()

def _circle_points(cx:float, cy:float, r:float) -> list[dict]:
    return [
        {"x": round(cx + r * math.cos(2 * math.pi * i / RING_SEGMENTS)), "y": round(cy + r * math.sin(2 * math.pi * i / RING_SEGMENTS))}
        for i in range(RING_SEGMENTS + 1)
    ]

def _rotate_to_heading(east:float, north:float, heading_rad:float) -> tuple[float, float]:
    """ Rotate a world-space (east, north) offset into a heading-up screen frame, where the
    player's current facing direction maps to "forward" (screen up) instead of true north. """
    sin_h, cos_h = math.sin(heading_rad), math.cos(heading_rad)
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
        """
        Real-world regression, confirmed against EDMCModernOverlay's actual overlay_api.py
        source: a newer release renamed define_plugin_group's kwargs (plugin_group ->
        plugin_name, matching_prefixes -> plugin_matching_prefixes, id_prefix_group ->
        plugin_group_name, id_prefixes -> plugin_group_prefixes -- the old snake_case names
        are still accepted as deprecated aliases, just logged as a warning) and requires
        plugin_group_prefixes whenever a new plugin_group_name is being created. An earlier fix
        here guessed the wrong replacement name (camelCase `idPrefixes`, which isn't a
        recognized argument under either name) -- confirmed correct against the real source.
        """
        if self._group_defined or not self.overlay.is_modern:
            return
        self._group_defined = self.overlay.define_group(
            plugin_name=PLUGIN_GROUP,
            plugin_matching_prefixes=[FRAME_PREFIX],
            plugin_group_name="ExplorerLite Radar",
            plugin_group_prefixes=[FRAME_PREFIX],
        )

    def render(self, store:ExplorerStore, state:ExplorerState) -> None:
        """ Shown as soon as a body is in view (SupercruiseExit onward, same as the panel's own
        exobiology section) -- not gated behind landed/on-foot, so it's already up guiding you
        in before you commit to landing, not just once you're already down. """
        if not self.overlay.available:
            self._log_skip("no overlay backend detected")
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

        # Genera come from the DB rather than state.sample_positions -- that's session-only and
        # only gains an entry once the FIRST sample is taken, so the radar would otherwise draw
        # nothing to guide you there. Confirmed (SAASignalsFound) takes priority; falls back to
        # the pre-DSS predicted genus so there's still something useful while still in the ship
        # -- but only when NOTHING has been confirmed yet (matches panel.py's own guard). Real
        # regression: falling back to predictions whenever there were no *active* genera (rather
        # than no genera confirmed AT ALL) meant a body with every genus already fully sampled
        # could resurrect a stale pre-DSS prediction and keep the radar showing, instead of
        # hiding once there's genuinely nothing left to scan.
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

        radius_px:int = _radius_px()
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
            elif SHOW_TAGGED_GENUS:
                self._draw_genus_ring(radius_px, genus, TAGGED_RING_COLOR)
                self._draw_genus_label(radius_px, genus)
        self._draw_player()

    def _active_genera(self, progress:list[sqlite3.Row]) -> list[str]:
        """ Every confirmed genus not yet fully sampled -- previously only the first one (in DB
        insertion order) was drawn, silently hiding both the current species' own already-taken
        samples (when a different, still-incomplete genus happened to sort first) and any other
        tagged species entirely. """
        return [row["genus"] for row in progress if not row["completed_at"]]

    def _predicted_genus(self, predictions:list[sqlite3.Row]) -> str|None:
        """ Best pre-DSS guess (highest confidence, already the query's own ordering). """
        return predictions[0]["genus"] if predictions else None

    def _draw_distance_rings(self, radius_px:int) -> None:
        for frac in (0.25, 0.5, 0.75, 1.0):
            r:float = radius_px * frac
            self.overlay.send_vect(f"{FRAME_PREFIX}ring-{frac}", _circle_points(CENTER_X, CENTER_Y, r), RING_COLOR, ttl=TTL)

    def _draw_genus_ring(self, radius_px:int, genus:str, color:str) -> None:
        min_dist:int|None = exobiology_data.genus_min_distance(genus)
        if not min_dist or min_dist > DISPLAY_RANGE_M:
            return
        r:float = radius_px * (min_dist / DISPLAY_RANGE_M)
        self.overlay.send_vect(f"{FRAME_PREFIX}ring-active-{genus}", _circle_points(CENTER_X, CENTER_Y, r), color, ttl=TTL)

    def _draw_genus_label(self, radius_px:int, genus:str) -> None:
        """ Only called when SHOW_TAGGED_GENUS is on -- see its docstring for why this is
        currently disabled (fixed screen anchor, easily mistaken for a bearing). """
        min_dist:int|None = exobiology_data.genus_min_distance(genus)
        if not min_dist or min_dist > DISPLAY_RANGE_M:
            return
        r:float = radius_px * (min_dist / DISPLAY_RANGE_M)
        self.overlay.send_text(f"{FRAME_PREFIX}label-{genus}", _genus_label(genus), LABEL_COLOR, CENTER_X - 10, round(CENTER_Y - r - 14), ttl=TTL)

    def _draw_player(self) -> None:
        self.overlay.send_shape(f"{FRAME_PREFIX}player", "rect", PLAYER_COLOR, PLAYER_COLOR, CENTER_X - 3, CENTER_Y - 3, 6, 6, ttl=TTL)

    def _draw_samples(self, state:ExplorerState, genus:str, radius_px:int, heading_rad:float) -> None:
        positions:list[tuple[float, float, str|None]] = state.sample_positions.get(genus, [])
        if not positions or state.planet_radius is None or state.latitude is None or state.longitude is None:
            return
        px_per_m:float = radius_px / DISPLAY_RANGE_M
        for i, (lat, lon, color_name) in enumerate(positions):
            east, north = local_offset_m(state.latitude, state.longitude, lat, lon, state.planet_radius)
            dist_m:float = math.hypot(east, north)
            in_range:bool = dist_m <= DISPLAY_RANGE_M
            if not in_range: # clamp to the ring's edge, same bearing, rather than drifting off-radar
                scale:float = DISPLAY_RANGE_M / dist_m
                east *= scale
                north *= scale
            forward, right = _rotate_to_heading(east, north, heading_rad)
            sx:float = CENTER_X + right * px_per_m
            sy:float = CENTER_Y - forward * px_per_m
            if not in_range: # push just past the outer ring line so it doesn't obscure the hollow marker
                dx, dy = sx - CENTER_X, sy - CENTER_Y
                edge_dist:float = math.hypot(dx, dy)
                if edge_dist > 0:
                    push:float = (edge_dist + SAMPLE_OUT_OF_RANGE_MARGIN_PX) / edge_dist
                    sx = CENTER_X + dx * push
                    sy = CENTER_Y + dy * push

            frame_id:str = f"{FRAME_PREFIX}sample-{genus}-{i}"
            if color_name is None:
                # a real sample -- filled/hollow square in the fixed sample color
                fill:str = SAMPLE_COLOR if in_range else "" # hollow once out of range -- position is only a bearing now, not exact
                self.overlay.send_shape(frame_id, "rect", SAMPLE_COLOR, fill, round(sx) - 3, round(sy) - 3, 6, 6, ttl=TTL)
            else:
                # a codex-tagged waypoint -- always-hollow triangle in the game's own reported
                # color; shape (not just color) is what keeps it from being mistaken for a
                # real sample, so the true color -- even a blue/cyan one -- is always safe here.
                self.overlay.send_vect(frame_id, _triangle_points(sx, sy, TAG_TRIANGLE_SIZE_PX), _tag_color(color_name), ttl=TTL)
