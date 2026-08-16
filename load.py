"""
EDMC-ExplorerLite: a lightweight exploration + exobiology assistant.
"""
import tkinter as tk

from config import config # type: ignore

from explorer.utils.debug import Debug
from explorer.utils.updater import Updater
from explorer.utils.overlay import Overlay

from explorer.constants import PLUGIN_NAME, PLUGIN_VERSION, GH_OWNER, GH_PROJECT, CFG_DEV_MODE
from explorer.db.store import ExplorerStore
from explorer.state import state as explorer_state
from explorer.journal.dispatch import dispatch
from explorer.journal.handlers_context import restore_last_session
from explorer.dashboard import on_dashboard_entry
from explorer.ui.panel import ExplorerPanel
from explorer.ui import prefs as prefs_ui
from explorer.ui.overlay_frames import RadarOverlay
from explorer.ui.overlay_summary import SystemSummaryOverlay
from explorer.ui.history_view import HistoryView

updater:Updater|None = None
store:ExplorerStore|None = None
panel:ExplorerPanel|None = None
radar:RadarOverlay|None = None
summary_overlay:SystemSummaryOverlay|None = None
history_view:HistoryView|None = None
overlay_backend:Overlay|None = None

def plugin_start3(plugin_dir:str) -> str:
    """ Load this plugin into EDMC """
    Debug(plugin_dir, config.get_bool(CFG_DEV_MODE, default=False))

    global updater, store, radar, overlay_backend
    updater = Updater(plugin_dir, GH_OWNER, GH_PROJECT)
    updater.check_for_update(PLUGIN_VERSION)
    store = ExplorerStore()
    overlay_backend = Overlay()
    radar = RadarOverlay(overlay_backend)

    return PLUGIN_NAME

def plugin_stop() -> None:
    """ EDMC is closing """
    if updater and updater.install_update:
        updater.install()
    if store:
        store.close()

def plugin_app(parent:tk.Frame) -> tk.Widget:
    """ Return a TK Frame for adding to the EDMC main window. """
    global panel, history_view, summary_overlay

    assert store is not None and overlay_backend is not None, "plugin_app called before plugin_start3"
    restore_last_session(store, explorer_state) # shows the last known system/body immediately, before any journal event
    panel = ExplorerPanel(parent, store, explorer_state)
    history_view = HistoryView(parent, store, explorer_state)
    panel.on_history_open = history_view.open
    summary_overlay = SystemSummaryOverlay(overlay_backend, panel) # needs panel's row formatting, so built after it
    return panel.frame

def plugin_prefs(parent:tk.Widget, cmdr:str, is_beta:bool) -> tk.Widget:
    """ Return a TK Frame for adding to the EDMC settings dialog. """
    overlay_available:bool = overlay_backend is not None and overlay_backend.available
    return prefs_ui.build_prefs(parent, cmdr, is_beta, overlay_available)

def prefs_changed(cmdr:str, is_beta:bool) -> None:
    """ Save settings. """
    prefs_ui.save_prefs(cmdr, is_beta)

def _apply_flags(flags:dict) -> None:
    if flags.get("panel") and panel is not None:
        panel.refresh()
    if flags.get("panel") and history_view is not None:
        history_view.refresh() # cheap no-op if the popup isn't open
    if flags.get("overlay") and store is not None:
        if radar is not None:
            radar.render(store, explorer_state)
        if summary_overlay is not None:
            summary_overlay.render(store, explorer_state) # same trigger as radar -- steady dashboard-tick cadence, not just discrete events

def journal_entry(cmdr:str, is_beta:bool, system:str, station:str, entry:dict, state:dict) -> None:
    """ Parse an incoming journal entry and update our own state/DB. `state` is EDMC's own
    per-Cmdr tracking, already updated for this entry. """
    if store is None:
        return
    _apply_flags(dispatch(store, explorer_state, cmdr, entry, state))

def dashboard_entry(cmdr:str, is_beta:bool, entry:dict) -> None:
    """ Handle dashboard (Status.json) state changes. """
    _apply_flags(on_dashboard_entry(explorer_state, entry))
