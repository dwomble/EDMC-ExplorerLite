""" Overlay system summary: mirrors the compact panel's system-summary header line plus a
capped list of flagged-body lines -- a glanceable "what's left to do here" without alt-tabbing
to the panel. Reuses ExplorerPanel._flagged_body_row() for the per-body text so both surfaces
never drift out of sync. """
from config import config # type: ignore

from explorer.utils.debug import Debug
from explorer.utils.overlay import Overlay

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.ui.panel import ExplorerPanel, system_header_line
from explorer.constants import CFG_OVERLAY_ENABLED, CFG_OVERLAY_SUMMARY_ENABLED

FRAME_PREFIX:str = "explorerlite-summary-"
PLUGIN_GROUP:str = "EDMC-ExplorerLite"

ANCHOR_X:int = 20
ANCHOR_Y:int = 20
LINE_HEIGHT_PX:int = 20
MAX_BODY_LINES:int = 6 # a sensible cap -- the overlay can't scroll like the panel's own table
TTL:int = 8 # matches overlay_frames.py's own TTL -- generous vs. the ~1/sec dashboard-tick refresh

HEADER_COLOR:str = "#ffffff"
BODY_LINE_COLOR:str = "#ffffff"
OVERFLOW_COLOR:str = "#999999" # same neutral grey as the radar's rings -- a subdued hint, not a data line

class SystemSummaryOverlay:
    """ Owns the overlay text frames. `panel` supplies the row formatting -- constructed after
    ExplorerPanel exists (see load.py's plugin_app), not in plugin_start3 alongside the radar. """

    def __init__(self, overlay:Overlay, panel:ExplorerPanel) -> None:
        self.overlay:Overlay = overlay
        self.panel:ExplorerPanel = panel
        self._group_defined:bool = False
        self._last_skip_reason:str|None = None # dedupe diagnostic logging -- log only on change

    def _log_skip(self, reason:str|None) -> None:
        if reason != self._last_skip_reason:
            self._last_skip_reason = reason
            if reason:
                Debug.logger.info(f"Summary overlay not drawing: {reason}")

    def _ensure_group(self) -> None:
        if self._group_defined or not self.overlay.is_modern:
            return
        self._group_defined = self.overlay.define_group(plugin_name=PLUGIN_GROUP, plugin_matching_prefixes=[FRAME_PREFIX],
            plugin_group_name="ExplorerLite Summary", plugin_group_prefixes=[FRAME_PREFIX])

    def render(self, store:ExplorerStore, state:ExplorerState) -> None:
        """ Shown whenever a system is known, same as the panel's own top-level gating -- not
        restricted to on-foot/landed like the radar, since "what's left in this system" is
        relevant throughout, not just while sampling. """
        if not self.overlay.available:
            self._log_skip("no overlay backend detected")
            return

        if not config.get_bool(CFG_OVERLAY_ENABLED, default=True):
            self._log_skip("overlay disabled in EDMC-ExplorerLite settings")
            return

        if not config.get_bool(CFG_OVERLAY_SUMMARY_ENABLED, default=True):
            self._log_skip("summary disabled in EDMC-ExplorerLite settings")
            return

        if state.system_id is None:
            self._log_skip("no system known yet")
            return

        system = store.get_system(state.system_id)
        if system is None:
            self._log_skip(f"system_id {state.system_id} not found in store")
            return

        self._log_skip(None) # clear -- we're drawing
        self._ensure_group()

        self.overlay.send_text(f"{FRAME_PREFIX}header", system_header_line(system), HEADER_COLOR, ANCHOR_X, ANCHOR_Y, ttl=TTL)

        rows:list[str] = []
        for body in store.get_flagged_bodies_for_system(system["id"]):
            row = self.panel._flagged_body_row(system["name"], body)
            if row is not None:
                rows.append(_format_body_line(row))

        shown:list[str] = rows[:MAX_BODY_LINES]
        for i, line in enumerate(shown):
            y:int = ANCHOR_Y + LINE_HEIGHT_PX * (i + 1)
            self.overlay.send_text(f"{FRAME_PREFIX}body-{i}", line, BODY_LINE_COLOR, ANCHOR_X, y, ttl=TTL)

        overflow:int = len(rows) - len(shown)
        if overflow > 0:
            y = ANCHOR_Y + LINE_HEIGHT_PX * (len(shown) + 1)
            self.overlay.send_text(f"{FRAME_PREFIX}overflow", f"+{overflow} more", OVERFLOW_COLOR, ANCHOR_X, y, ttl=TTL)
        # No explicit clear for rows/overflow beyond the current count -- same as overlay_frames.py,
        # a stale line just stops being refreshed and expires via its own TTL.

def _format_body_line(row:tuple[str, str, str, str, str]) -> str:
    """ Collapses _flagged_body_row()'s (designator, distance, gravity, value, description)
    tuple to name/value/what's-left-to-do -- distance and gravity are on the panel's own table
    columns already, not worth the overlay's limited width. """
    designator, _distance, _gravity, value_str, species_desc = row
    return f"{designator}  {value_str}  {species_desc}" if species_desc else f"{designator}  {value_str}"
