"""
Overlay radar: distance rings on a fixed real-world scale, a highlighted ring at the current
species' required minimum sample distance, and cross markers per logged sample. Visible from
SupercruiseExit onward (flying over the surface, not just on-foot) whenever a confirmed genus
has at least one sample taken this visit -- a genus that's merely been tagged via
SAASignalsFound but not yet approached this visit draws nothing by default (see
SHOW_TAGGED_GENUS): there's no known bearing to it yet, only a distance, and showing a
differently-colored ring + label for it either conveyed no real information or (once heading-up
was added) misleadingly suggested a direction, since the label's fixed screen anchor always
coincided with "straight ahead". Draws every not-yet-completed genus that IS in progress at
once (not just one) so it keeps guiding you to each simultaneously, showing samples already
taken for each. Built on the generic utils/overlay.py wrapper -- this module supplies
EDMC-ExplorerLite's own frame names, positions, and colors, which is deliberately NOT part of
the shared library (see PluginLib's overlay.py docstring).

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
SAMPLE_COLOR:str = "#00aaff"
PLAYER_COLOR:str = "#ffffff"
LABEL_COLOR:str = "#ffffff"

def _genus_label(genus:str) -> str:
    """ First 3 letters, uppercased -- confirmed unique across all 21 known genera in
    exobiology_data.py, so it's enough to tell simultaneously-drawn genera apart at a glance. """
    return genus[:3].upper()

def _circle_points(cx:float, cy:float, r:float) -> list[dict]:
    return [
        {"x": round(cx + r * math.cos(2 * math.pi * i / RING_SEGMENTS)), "y": round(cy + r * math.sin(2 * math.pi * i / RING_SEGMENTS))}
        for i in range(RING_SEGMENTS + 1)
    ]

def _local_xy_m(lat0:float, lon0:float, lat:float, lon:float, planet_radius_m:float) -> tuple[float, float]:
    """ Flat-earth approximation, meters east (x) / north (y) from (lat0, lon0) -- fine at the scale of exobiology sample distances. """
    y:float = math.radians(lat - lat0) * planet_radius_m
    x:float = math.radians(lon - lon0) * planet_radius_m * math.cos(math.radians(lat0))
    return x, y

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
        # the pre-DSS predicted genus so there's still something useful while still in the ship.
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        genera:list[str] = self._active_genera(store.get_species_progress_for_body(body_pk))
        if not genera:
            predicted:str|None = self._predicted_genus(store.get_genus_predictions_for_body(body_pk))
            genera = [predicted] if predicted else []
        if not genera:
            self._log_skip(f"no confirmed or predicted genus yet for body {state.body_name!r} (body_pk={body_pk})")
            return

        self._log_skip(None) # clear -- we're drawing
        self._ensure_group()

        radius_px:int = _radius_px()
        heading_rad:float = math.radians(state.heading) if state.heading is not None else 0.0
        self._draw_distance_rings(radius_px)
        for genus in genera:
            in_progress:bool = bool(state.sample_positions.get(genus))
            if in_progress:
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
        positions:list[tuple[float, float]] = state.sample_positions.get(genus, [])
        if not positions or state.planet_radius is None or state.latitude is None or state.longitude is None:
            return
        px_per_m:float = radius_px / DISPLAY_RANGE_M
        for i, (lat, lon) in enumerate(positions):
            east, north = _local_xy_m(state.latitude, state.longitude, lat, lon, state.planet_radius)
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
            fill:str = SAMPLE_COLOR if in_range else "" # hollow once out of range -- position is only a bearing now, not exact
            self.overlay.send_shape(f"{FRAME_PREFIX}sample-{genus}-{i}", "rect", SAMPLE_COLOR, fill, round(sx) - 3, round(sy) - 3, 6, 6, ttl=TTL)
