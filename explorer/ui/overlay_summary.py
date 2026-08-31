""" Overlay mirror of ExplorerPanel's system summary: header, flagged bodies, current body. """
import sqlite3

from config import config # type: ignore

from explorer.utils.debug import Debug
from explorer.utils.overlay import Overlay

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.ui.panel import ExplorerPanel, system_status_text, system_body_count_text, flagged_body_sort_key
from explorer.constants import (
    CFG_PANEL_ENABLED, CFG_OVERLAY_SUMMARY_ENABLED,
    CFG_OVERLAY_SUMMARY_TEXT_COLOR, DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR,
)

FRAME_PREFIX:str = "explorerlite-summary-"
PLUGIN_GROUP:str = "EDMC-ExplorerLite"

ANCHOR_X:int = 20
ANCHOR_Y:int = 20
LINE_HEIGHT_PX:int = 20
HEADER_LINE_HEIGHT_PX:int = 25 # "large" text needs more room than LINE_HEIGHT_PX
CURRENT_BODY_INDENT_PX:int = 20 # matches panel's own indent treatment
MAX_BODY_LINES:int = 6 # no scrolling on the overlay, unlike the panel

TTL:int = 300
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

        if not config.get_bool(CFG_PANEL_ENABLED, default=True):
            self._log_skip("panel hidden via the show/hide toggle")
            self._clear_all()
            return

        if not config.get_bool(CFG_OVERLAY_SUMMARY_ENABLED, default=True):
            self._log_skip("summary disabled in EDMC-ExplorerLite settings")
            self._clear_all()
            return

        if not state.overlay_relevant:
            self._log_skip("docked, on-foot in a station, or a UI panel has focus")
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

        body_count:str = system_body_count_text(system)
        header_text:str = f"{body_count} — {system_status_text(store, system)}" if body_count else system_status_text(store, system)
        self.overlay.send_text(f"{FRAME_PREFIX}header", header_text, color, ANCHOR_X, ANCHOR_Y, ttl=TTL, size="large")
        self._last_had_header = True
        next_y:int = ANCHOR_Y + HEADER_LINE_HEIGHT_PX

        flagged:list[sqlite3.Row] = sorted(store.get_flagged_bodies_for_system(system["id"]), key=flagged_body_sort_key)
        rows:list[tuple[int, str]] = []
        for body in flagged:
            row = self.panel._flagged_body_row(system["name"], body)
            if row is not None:
                rows.append((body["body_id"], _format_body_line(row)))

        shown:list[tuple[int, str]] = rows[:MAX_BODY_LINES]
        current_lines:list[str] = self._current_body_lines(store, state)
        current_shown:bool = False # nests under the focus body, matching the panel
        for i, (body_id, line) in enumerate(shown):
            self.overlay.send_text(f"{FRAME_PREFIX}body-{i}", line, color, ANCHOR_X, next_y, ttl=TTL)
            next_y += LINE_HEIGHT_PX
            if body_id == state.exobio_focus_body_id:
                next_y = self._send_current_lines(current_lines, color, next_y)
                current_shown = True
        for i in range(len(shown), self._last_body_count): # clear slots dropped since last render
            self.overlay.clear(f"{FRAME_PREFIX}body-{i}")
        self._last_body_count = len(shown)

        overflow:int = len(rows) - len(shown)
        if overflow > 0:
            self.overlay.send_text(f"{FRAME_PREFIX}overflow", f"+{overflow} more", OVERFLOW_COLOR, ANCHOR_X, next_y, ttl=TTL)
            next_y += LINE_HEIGHT_PX
        elif self._last_had_overflow:
            self.overlay.clear(f"{FRAME_PREFIX}overflow")
        self._last_had_overflow = overflow > 0

        if not current_shown: # current body wasn't in shown -- e.g. bumped to overflow
            self._send_current_lines(current_lines, color, next_y)
        for i in range(len(current_lines), self._last_current_count):
            self.overlay.clear(f"{FRAME_PREFIX}current-{i}")
        self._last_current_count = len(current_lines)

    def _send_current_lines(self, lines:list[str], color:str, y:int) -> int:
        for i, line in enumerate(lines):
            self.overlay.send_text(f"{FRAME_PREFIX}current-{i}", line, color, ANCHOR_X + CURRENT_BODY_INDENT_PX, y, ttl=TTL)
            y += LINE_HEIGHT_PX
        return y

    def _current_body_lines(self, store:ExplorerStore, state:ExplorerState) -> list[str]:
        """ Mirrors panel's exobio-section selection logic. """
        focus_id:int|None = state.exobio_focus_body_id
        if state.cmdr_id is None or state.system_id is None or focus_id is None:
            return []

        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, focus_id, state.exobio_focus_body_name)
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

def _format_body_line(row:tuple[str, str, str, str, str]) -> str:
    """ Same columns as the panel's own flagged-body table. """
    designator, distance, gravity, value_str, species_desc = row
    line:str = f"{designator}  {distance}  {gravity}  {value_str}"
    return f"{line}  {species_desc}" if species_desc else line

def _format_progress_line(row:tuple[str, str, str, str]) -> str:
    """ Formats an _exobio_progress_row() tuple. """
    progress, name, distance, value_str = row
    return f"{progress}  {name}  {distance}  {value_str}"

def _format_predicted_line(row:tuple[str, str, str]) -> str:
    """ Formats a _predicted_genus_row() tuple. """
    name, distance, value_str = row
    return f"{name}  {distance}  {value_str}"
