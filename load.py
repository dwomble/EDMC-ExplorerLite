"""
EDMC-ExplorerLite: a lightweight exploration + exobiology assistant.
"""
import tkinter as tk

from config import config # type: ignore

from explorer.utils.debug import Debug
from explorer.utils.updater import Updater
from explorer.utils.overlay import Overlay

from explorer.constants import PLUGIN_NAME, PLUGIN_VERSION, GH_PROJECT, CFG_DEV_MODE
from explorer.db.store import ExplorerStore
from explorer.state import state as explorer_state
from explorer.journal.dispatch import dispatch
from explorer.dashboard import on_dashboard_entry
from explorer.ui.panel import ExplorerPanel
from explorer.ui import prefs as prefs_ui
from explorer.ui.overlay_frames import RadarOverlay
from explorer.ui.history_view import HistoryView

updater:Updater|None = None
store:ExplorerStore|None = None
panel:ExplorerPanel|None = None
radar:RadarOverlay|None = None
history_view:HistoryView|None = None

def plugin_start3(plugin_dir:str) -> str:
    """ Load this plugin into EDMC """
    Debug(plugin_dir, config.get_bool(CFG_DEV_MODE, default=False))

    global updater, store, radar
    updater = Updater(plugin_dir, GH_PROJECT)
    updater.check_for_update(PLUGIN_VERSION)
    store = ExplorerStore()
    radar = RadarOverlay(Overlay())

    return PLUGIN_NAME

def plugin_stop() -> None:
    """ EDMC is closing """
    if updater and updater.install_update:
        updater.install()
    if store:
        store.close()

def plugin_app(parent:tk.Frame):
    """ Return a TK Frame for adding to the EDMC main window. """
    global panel, history_view
    assert store is not None, "plugin_app called before plugin_start3"
    panel = ExplorerPanel(parent, store, explorer_state)
    history_view = HistoryView(parent, store, explorer_state)
    panel.on_history_open = history_view.open
    return panel.frame

def plugin_prefs(parent, cmdr:str, is_beta:bool):
    """ Return a TK Frame for adding to the EDMC settings dialog. """
    return prefs_ui.build_prefs(parent, cmdr, is_beta)

def prefs_changed(cmdr:str, is_beta:bool) -> None:
    """ Save settings. """
    prefs_ui.save_prefs(cmdr, is_beta)

def _apply_flags(flags:dict) -> None:
    if flags.get("panel"):
        if panel is not None:
            panel.refresh()
        if history_view is not None:
            history_view.refresh() # cheap no-op if the popup isn't open
    if flags.get("overlay") and radar is not None:
        radar.render(explorer_state)

def journal_entry(cmdr:str, is_beta:bool, system:str, station:str, entry:dict, state:dict) -> None:
    """ Parse an incoming journal entry and update our own state/DB. """
    if store is None:
        return
    explorer_state.is_beta = is_beta
    _apply_flags(dispatch(store, explorer_state, cmdr, entry))

def dashboard_entry(cmdr:str, is_beta:bool, entry:dict) -> None:
    """ Handle dashboard (Status.json) state changes. """
    _apply_flags(on_dashboard_entry(explorer_state, entry))
