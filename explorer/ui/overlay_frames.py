"""
Overlay radar: distance rings, a highlighted ring at the active genus's required minimum
sample distance, cross markers per logged sample, and a heading tick. Visible from
SupercruiseExit onward (flying over the surface, not just on-foot) whenever there's a
confirmed or predicted genus to show. Built on the generic utils/overlay.py wrapper -- this
module supplies EDMC-ExplorerLite's own frame names, positions, and colors, which is
deliberately NOT part of the shared library (see PluginLib's overlay.py docstring).

North-up, not rotated to the player's heading -- the heading tick alone shows facing
direction. Sample markers are positioned relative to the player's CURRENT position each call,
so they correctly drift as the player walks around, same as a real radar.

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
from explorer.constants import CFG_OVERLAY_ENABLED, CFG_OVERLAY_RADAR_ENABLED

FRAME_PREFIX:str = "explorerlite-radar-"
PLUGIN_GROUP:str = "EDMC-ExplorerLite"

CENTER_X:int = 640
CENTER_Y:int = 480
RADIUS_PX:int = 150 # on-screen pixel radius for the radar's max display range
RING_SEGMENTS:int = 24
TTL:int = 4

RING_COLOR:str = "#00ff00"
ACTIVE_RING_COLOR:str = "#ffaa00"
SAMPLE_COLOR:str = "#00aaff"
PLAYER_COLOR:str = "#ffffff"
HEADING_COLOR:str = "#ffffff"

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

        # Genus comes from the DB rather than state.sample_positions -- that's session-only and
        # only gains an entry once the FIRST sample is taken, so the radar would otherwise draw
        # nothing to guide you there. Confirmed (SAASignalsFound) takes priority; falls back to
        # the pre-DSS predicted genus so there's still something useful while still in the ship.
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        genus:str|None = self._active_genus(store.get_species_progress_for_body(body_pk)) \
            or self._predicted_genus(store.get_genus_predictions_for_body(body_pk))
        if genus is None:
            self._log_skip(f"no confirmed or predicted genus yet for body {state.body_name!r} (body_pk={body_pk})")
            return

        self._log_skip(None) # clear -- we're drawing
        self._ensure_group()

        display_range:float = self._display_range(genus)
        self._draw_rings(display_range, genus)
        self._draw_heading_tick(state.heading)
        self._draw_player()
        self._draw_samples(state, genus, display_range)

    def _active_genus(self, progress:list[sqlite3.Row]) -> str|None:
        """ Prefer a genus that isn't done yet; fall back to whatever's tracked for this body. """
        for row in progress:
            if not row["completed_at"]:
                return row["genus"]
        return progress[0]["genus"] if progress else None

    def _predicted_genus(self, predictions:list[sqlite3.Row]) -> str|None:
        """ Best pre-DSS guess (highest confidence, already the query's own ordering). """
        return predictions[0]["genus"] if predictions else None

    def _display_range(self, genus:str) -> float:
        min_dist:int = exobiology_data.genus_min_distance(genus) or 200
        return max(min_dist * 1.5, 100)

    def _draw_rings(self, display_range:float, genus:str) -> None:
        for frac in (0.25, 0.5, 0.75, 1.0):
            r:float = RADIUS_PX * frac
            self.overlay.send_vect(f"{FRAME_PREFIX}ring-{frac}", _circle_points(CENTER_X, CENTER_Y, r), RING_COLOR, ttl=TTL)

        min_dist:int|None = exobiology_data.genus_min_distance(genus)
        if min_dist and min_dist <= display_range:
            r:float = RADIUS_PX * (min_dist / display_range)
            self.overlay.send_vect(f"{FRAME_PREFIX}ring-active", _circle_points(CENTER_X, CENTER_Y, r), ACTIVE_RING_COLOR, ttl=TTL)

    def _draw_player(self) -> None:
        self.overlay.send_shape(f"{FRAME_PREFIX}player", "rect", PLAYER_COLOR, PLAYER_COLOR, CENTER_X - 3, CENTER_Y - 3, 6, 6, ttl=TTL)

    def _draw_heading_tick(self, heading:float|None) -> None:
        if heading is None:
            return
        rad:float = math.radians(heading)
        tick_len:int = RADIUS_PX + 15
        x2:int = round(CENTER_X + math.sin(rad) * tick_len)
        y2:int = round(CENTER_Y - math.cos(rad) * tick_len)
        self.overlay.send_vect(f"{FRAME_PREFIX}heading", [{"x": CENTER_X, "y": CENTER_Y}, {"x": x2, "y": y2}], HEADING_COLOR, ttl=TTL)

    def _draw_samples(self, state:ExplorerState, genus:str, display_range:float) -> None:
        positions:list[tuple[float, float]] = state.sample_positions.get(genus, [])
        if not positions or state.planet_radius is None or state.latitude is None or state.longitude is None:
            return
        px_per_m:float = RADIUS_PX / display_range
        for i, (lat, lon) in enumerate(positions):
            x, y = _local_xy_m(state.latitude, state.longitude, lat, lon, state.planet_radius)
            sx:int = round(CENTER_X + x * px_per_m)
            sy:int = round(CENTER_Y - y * px_per_m)
            self.overlay.send_shape(f"{FRAME_PREFIX}sample-{i}", "rect", SAMPLE_COLOR, SAMPLE_COLOR, sx - 3, sy - 3, 6, 6, ttl=TTL)
