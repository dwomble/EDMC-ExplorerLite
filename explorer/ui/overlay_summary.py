""" Overlay mirror of ExplorerPanel's system summary: header, flagged bodies, current body. """
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
CURRENT_BODY_INDENT_PX:int = 20 # matches panel's own indent treatment
MAX_BODY_LINES:int = 6 # no scrolling on the overlay, unlike the panel
MAX_CURRENT_BODY_LINES:int = 6

TTL:int = 30 # longer than radar's TTL -- refreshes were too sparse
OVERFLOW_COLOR:str = "#999999" # same grey as radar's rings, a subdued hint

def _text_color() -> str:
    return config.get_str(CFG_OVERLAY_SUMMARY_TEXT_COLOR, default=DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR)

class SystemSummaryOverlay:
    """ Owns overlay frames; built after ExplorerPanel exists. """

    def __init__(self, overlay:Overlay, panel:ExplorerPanel) -> None:
        self.overlay:Overlay = overlay
        self.panel:ExplorerPanel = panel
        self._group_defined:bool = False
        self._last_skip_reason:str|None = None
        self._last_had_header:bool = False
        self._last_body_count:int = 0
        self._last_had_overflow:bool = False
        self._last_current_count:int = 0

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

    def _clear_all(self) -> None:
        """ Clears every slot from the last render(). """
        if self._last_had_header:
            self.overlay.clear(f"{FRAME_PREFIX}header")
        for i in range(self._last_body_count):
            self.overlay.clear(f"{FRAME_PREFIX}body-{i}")
        if self._last_had_overflow:
            self.overlay.clear(f"{FRAME_PREFIX}overflow")
        for i in range(self._last_current_count):
            self.overlay.clear(f"{FRAME_PREFIX}current-{i}")
        self._last_had_header = False
        self._last_body_count = 0
        self._last_had_overflow = False
        self._last_current_count = 0

    def render(self, store:ExplorerStore, state:ExplorerState) -> None:
        """ Shown for any known system, not gated to on-foot like the radar. """
        if not self.overlay.available:
            self._log_skip("no overlay backend detected")
            return

        if not config.get_bool(CFG_OVERLAY_ENABLED, default=True):
            self._log_skip("overlay disabled in EDMC-ExplorerLite settings")
            self._clear_all()
            return

        if not config.get_bool(CFG_OVERLAY_SUMMARY_ENABLED, default=True):
            self._log_skip("summary disabled in EDMC-ExplorerLite settings")
            self._clear_all()
            return

        if state.system_id is None:
            self._log_skip("no system known yet")
            self._clear_all()
            return

        system = store.get_system(state.system_id)
        if system is None:
            self._log_skip(f"system_id {state.system_id} not found in store")
            self._clear_all()
            return

        self._log_skip(None)
        self._ensure_group()
        color:str = _text_color()

        scanned_count:int = store.count_scanned_bodies_for_system(system["id"])
        self.overlay.send_text(f"{FRAME_PREFIX}header", system_status_text(system, scanned_count), color, ANCHOR_X, ANCHOR_Y, ttl=TTL)
        self._last_had_header = True

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
        for i in range(len(shown), self._last_body_count): # clear slots dropped since last render
            self.overlay.clear(f"{FRAME_PREFIX}body-{i}")
        self._last_body_count = len(shown)

        next_row:int = len(shown) + 1
        overflow:int = len(rows) - len(shown)
        if overflow > 0:
            self.overlay.send_text(f"{FRAME_PREFIX}overflow", f"+{overflow} more", OVERFLOW_COLOR, ANCHOR_X, ANCHOR_Y + LINE_HEIGHT_PX * next_row, ttl=TTL)
            next_row += 1
        elif self._last_had_overflow:
            self.overlay.clear(f"{FRAME_PREFIX}overflow")
        self._last_had_overflow = overflow > 0

        current_lines:list[str] = self._current_body_lines(store, state)[:MAX_CURRENT_BODY_LINES]
        for i, line in enumerate(current_lines):
            y = ANCHOR_Y + LINE_HEIGHT_PX * (next_row + i)
            self.overlay.send_text(f"{FRAME_PREFIX}current-{i}", line, color, ANCHOR_X + CURRENT_BODY_INDENT_PX, y, ttl=TTL)
        for i in range(len(current_lines), self._last_current_count):
            self.overlay.clear(f"{FRAME_PREFIX}current-{i}")
        self._last_current_count = len(current_lines)

    def _current_body_lines(self, store:ExplorerStore, state:ExplorerState) -> list[str]:
        """ Mirrors panel's exobio-section selection logic. """
        if state.cmdr_id is None or state.system_id is None or state.body_id is None:
            return []

        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
        all_progress:list[sqlite3.Row] = store.get_species_progress_for_body(body_pk)
        active:list[sqlite3.Row] = [row for row in all_progress if not row["completed_at"]]
        predictions:list[dict] = [] if (active or all_progress) else self.panel._best_predictions_for_body(body_pk)

        if not active and all_progress:
            return [] # fully sampled, nothing left to do

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

        return []

def _sort_key(body:sqlite3.Row) -> bool:
    """ Biological bodies sort first so they don't overflow. """
    biological:bool = bool(body["has_biological_signals"] == 1 or body["flagged_exobio"] or body["has_prediction"])
    return not biological

def _format_body_line(row:tuple[str, str, str, str, str]) -> str:
    """ Collapses the row tuple to name/value/species text. """
    designator, _distance, _gravity, value_str, species_desc = row
    return f"{designator}  {value_str}  {species_desc}" if species_desc else f"{designator}  {value_str}"

def _format_progress_line(row:tuple[str, str, str, str]) -> str:
    """ Formats an _exobio_progress_row() tuple. """
    name, progress, distance, value_str = row
    return f"{name}  {progress}  {distance}  {value_str}"

def _format_predicted_line(row:tuple[str, str, str]) -> str:
    """ Formats a _predicted_genus_row() tuple. """
    name, distance, value_str = row
    return f"{name}  {distance}  {value_str}"
