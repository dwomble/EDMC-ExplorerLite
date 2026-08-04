"""
Overlay radar: distance rings, a highlighted ring at the active genus's required minimum
sample distance, cross markers per logged sample, and a heading tick. Built on the generic
utils/overlay.py wrapper -- this module supplies EDMC-ExplorerLite's own frame names,
positions, and colors, which is deliberately NOT part of the shared library (see PluginLib's
overlay.py docstring).

North-up, not rotated to the player's heading -- the heading tick alone shows facing
direction. Sample markers are positioned relative to the player's CURRENT position each call,
so they correctly drift as the player walks around, same as a real radar.

No explicit "clear" -- every shape is sent with a short TTL and simply stops being refreshed
(and expires on the overlay) once render() stops being called for this genus/body, which
happens naturally once the panel/dispatch flags say the overlay is no longer relevant.
"""
import math

from config import config # type: ignore

from explorer.utils.overlay import Overlay

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

    def _ensure_group(self) -> None:
        if self._group_defined or not self.overlay.is_modern:
            return
        self._group_defined = self.overlay.define_group(
            plugin_group=PLUGIN_GROUP,
            matching_prefixes=[FRAME_PREFIX],
            id_prefix_group="ExplorerLite Radar",
        )

    def render(self, state:ExplorerState) -> None:
        if not self.overlay.available:
            return
        if not config.get_bool(CFG_OVERLAY_ENABLED, default=True) or not config.get_bool(CFG_OVERLAY_RADAR_ENABLED, default=True):
            return
        if not state.exobiology_relevant or not state.has_lat_long or state.latitude is None or state.longitude is None:
            return

        genus:str|None = self._active_genus(state)
        if genus is None:
            return

        self._ensure_group()

        display_range:float = self._display_range(genus)
        self._draw_rings(display_range, genus)
        self._draw_heading_tick(state.heading)
        self._draw_player()
        self._draw_samples(state, genus, display_range)

    def _active_genus(self, state:ExplorerState) -> str|None:
        """ Prefer a genus that isn't done yet; fall back to whatever's tracked this visit. """
        for genus, positions in state.sample_positions.items():
            if len(positions) < 3:
                return genus
        if state.sample_positions:
            return next(iter(state.sample_positions))
        return None

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
