""" Overlay system summary: mirrors the compact panel's system-summary header line, a capped
list of flagged-body lines, and the current body's own per-species detail (indented under the
list, no header -- same nesting as the panel's own table) -- a glanceable "what's left to do
here" without alt-tabbing to the panel. Reuses ExplorerPanel's own row-building methods for all
of this so the overlay text never drifts out of sync with the panel. """
import sqlite3

from config import config # type: ignore

from explorer.utils.debug import Debug
from explorer.utils.overlay import Overlay

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.ui.panel import ExplorerPanel, system_status_text
from explorer.constants import (
    CFG_OVERLAY_ENABLED, CFG_OVERLAY_SUMMARY_ENABLED,
    CFG_OVERLAY_SUMMARY_TEXT_COLOR, DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR,
)

FRAME_PREFIX:str = "explorerlite-summary-"
PLUGIN_GROUP:str = "EDMC-ExplorerLite"

ANCHOR_X:int = 20
ANCHOR_Y:int = 20
LINE_HEIGHT_PX:int = 20
CURRENT_BODY_INDENT_PX:int = 20 # nests the current body's species lines under the list, no header -- matches the panel's own INDENT_PX treatment
MAX_BODY_LINES:int = 6 # a sensible cap -- the overlay can't scroll like the panel's own table
MAX_CURRENT_BODY_LINES:int = 6 # ditto, for the current body's own species detail below the list
TTL:int = 30 # longer than overlay_frames.py's radar TTL (8s) -- real-world reports of the
# summary going blank between refreshes even though it's on the same dashboard-tick trigger as
# the radar; a longer TTL is a safe hedge against however irregular that cadence turns out to be

OVERFLOW_COLOR:str = "#999999" # same neutral grey as the radar's rings -- a subdued hint, not a data line

def _text_color() -> str:
    return config.get_str(CFG_OVERLAY_SUMMARY_TEXT_COLOR, default=DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR)

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
        color:str = _text_color()

        scanned_count:int = store.count_scanned_bodies_for_system(system["id"])
        self.overlay.send_text(f"{FRAME_PREFIX}header", system_status_text(system, scanned_count), color, ANCHOR_X, ANCHOR_Y, ttl=TTL)

        flagged:list[sqlite3.Row] = sorted(store.get_flagged_bodies_for_system(system["id"]), key=_sort_key)
        rows:list[str] = []
        for body in flagged:
            row = self.panel._flagged_body_row(system["name"], body)
            if row is not None:
                rows.append(_format_body_line(row))

        shown:list[str] = rows[:MAX_BODY_LINES]
        for i, line in enumerate(shown):
            y:int = ANCHOR_Y + LINE_HEIGHT_PX * (i + 1)
            self.overlay.send_text(f"{FRAME_PREFIX}body-{i}", line, color, ANCHOR_X, y, ttl=TTL)

        next_row:int = len(shown) + 1
        overflow:int = len(rows) - len(shown)
        if overflow > 0:
            self.overlay.send_text(f"{FRAME_PREFIX}overflow", f"+{overflow} more", OVERFLOW_COLOR, ANCHOR_X, ANCHOR_Y + LINE_HEIGHT_PX * next_row, ttl=TTL)
            next_row += 1
        # No explicit clear for rows/overflow beyond the current count -- same as overlay_frames.py,
        # a stale line just stops being refreshed and expires via its own TTL.

        current_lines:list[str] = self._current_body_lines(store, state)[:MAX_CURRENT_BODY_LINES]
        for i, line in enumerate(current_lines):
            y = ANCHOR_Y + LINE_HEIGHT_PX * (next_row + i)
            self.overlay.send_text(f"{FRAME_PREFIX}current-{i}", line, color, ANCHOR_X + CURRENT_BODY_INDENT_PX, y, ttl=TTL)

    def _current_body_lines(self, store:ExplorerStore, state:ExplorerState) -> list[str]:
        """ Mirrors ExplorerPanel._render_exobiology_section()'s own selection logic exactly
        (active samples this visit, else a pre-DSS prediction, else nothing) -- reusing its row
        methods directly rather than re-deriving the same value/formatting logic here. No
        header/body-name line, same as the panel's own nesting -- just the indented x offset
        (see render()) ties these lines back to the body above them. """
        if state.cmdr_id is None or state.system_id is None or state.body_id is None:
            return []

        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        all_progress:list[sqlite3.Row] = store.get_species_progress_for_body(body_pk)
        active:list[sqlite3.Row] = [row for row in all_progress if not row["completed_at"]]
        predictions:list[dict] = [] if (active or all_progress) else self.panel._best_predictions_for_body(body_pk)

        if not active and all_progress:
            return [] # every genus here is fully sampled -- nothing left to do

        if not active and not predictions and not state.on_foot:
            return []

        body:sqlite3.Row|None = store.get_body(body_pk)
        was_footfalled:bool = bool(body and body["was_footfalled"])

        if active:
            rows = [self.panel._exobio_progress_row(row, was_footfalled) for row in active]
            return [_format_progress_line(r) for r in rows]

        if predictions:
            confirmed_signal:bool = bool(body and body["has_biological_signals"])
            rows = [self.panel._predicted_genus_row(slot, confirmed_signal, was_footfalled) for slot in predictions]
            return [_format_predicted_line(r) for r in rows]

        return ["No genus detected yet"]

def _sort_key(body:sqlite3.Row) -> bool:
    """ Biologically-interesting bodies first -- MAX_BODY_LINES is a hard cap with no
    scrolling, so a system with several cartography-flagged bodies must never silently push
    exobiology (this plugin's whole point) into the anonymous overflow count. Stable sort, so
    body_id order is otherwise preserved within each group. """
    biological:bool = bool(body["has_biological_signals"] == 1 or body["flagged_exobio"] or body["has_prediction"])
    return not biological

def _format_body_line(row:tuple[str, str, str, str, str]) -> str:
    """ Collapses _flagged_body_row()'s (designator, distance, gravity, value, description)
    tuple to name/value/what's-left-to-do -- distance and gravity are on the panel's own table
    columns already, not worth the overlay's limited width. """
    designator, _distance, _gravity, value_str, species_desc = row
    return f"{designator}  {value_str}  {species_desc}" if species_desc else f"{designator}  {value_str}"

def _format_progress_line(row:tuple[str, str, str, str]) -> str:
    """ _exobio_progress_row()'s (name, samples-taken progress, min-distance, value) tuple. """
    name, progress, distance, value_str = row
    return f"{name}  {progress}  {distance}  {value_str}"

def _format_predicted_line(row:tuple[str, str, str]) -> str:
    """ _predicted_genus_row()'s (name, min-distance, value) tuple. """
    name, distance, value_str = row
    return f"{name}  {distance}  {value_str}"
