"""
EDMC-ExplorerLite: a lightweight exploration + exobiology assistant.
"""
import tkinter as tk

from config import config # type: ignore

from explorer.utils.debug import Debug
from explorer.utils.updater import Notices, Updater, read_version_file
from explorer.utils.overlay import Overlay

from explorer.constants import PLUGIN_NAME, GH_OWNER, GH_PROJECT, CFG_DEV_MODE
from explorer.context import Context
from explorer.db.store import ExplorerStore
from explorer.state import state as explorer_state
from explorer.util import now_iso, format_pending_credits
from explorer.journal.dispatch import dispatch
from explorer.journal.handlers_context import restore_last_session
from explorer.journal.handlers_sales import mark_everything_unsold_lost
from explorer.dashboard import on_dashboard_entry
from explorer.ui.panel import ExplorerPanel
from explorer.ui import prefs as prefs_ui
from explorer.ui.overlay_frames import RadarOverlay
from explorer.ui.overlay_summary import SystemSummaryOverlay
from explorer.ui.history_view import HistoryView

VERSION:str = "0.0.0" # placeholder -- plugin_start3() overwrites this

def plugin_start3(plugin_dir:str) -> str:
    """ Load this plugin into EDMC """
    global VERSION
    version = read_version_file(plugin_dir, "0.0.0")
    VERSION = str(version)

    Debug(plugin_dir, config.get_bool(CFG_DEV_MODE, default=False))

    Context.updater = Updater(plugin_dir, GH_OWNER, GH_PROJECT)
    Context.updater.check_for_update(version)
    Context.notices = Notices(GH_OWNER, GH_PROJECT)
    Context.notices.check_for_notices()
    Context.store = ExplorerStore()
    Context.overlay_backend = Overlay()
    Context.radar = RadarOverlay(Context.overlay_backend)

    return PLUGIN_NAME

def plugin_stop() -> None:
    """ EDMC is closing """
    if Context.updater and Context.updater.install_update:
        Context.updater.install()
    if Context.store:
        Context.store.close()
    Context.reset()

def plugin_app(parent:tk.Frame) -> tk.Widget:
    """ Return a TK Frame for adding to the EDMC main window. """
    assert Context.store is not None and Context.overlay_backend is not None, "plugin_app called before plugin_start3"
    restore_last_session(Context.store, explorer_state) # shows the last known system/body immediately, before any journal event
    Context.panel = ExplorerPanel(parent, Context.store, explorer_state, Context.notices)
    Context.history_view = HistoryView(parent, Context.store, explorer_state)
    Context.panel.on_history_open = Context.history_view.open
    Context.summary_overlay = SystemSummaryOverlay(Context.overlay_backend, Context.panel) # needs panel's row formatting, so built after it
    return Context.panel.frame

def _clear_unsold_data(cmdr:str) -> str:
    """ For a death EDMC never saw, e.g. it wasn't running. """
    if Context.store is None: return "No data stored."

    cmdr_id:int = Context.store.get_or_create_cmdr(cmdr)
    cart_pending:int = Context.store.get_pending_cartography_value(cmdr_id)
    exo_pending:int = Context.store.get_pending_exobiology_value(cmdr_id)
    mark_everything_unsold_lost(Context.store, cmdr_id, now_iso())

    if Context.panel is not None:
        Context.panel.refresh()
    if Context.history_view is not None:
        Context.history_view.refresh()

    return f"Marked {format_pending_credits(cart_pending)} cartography and {format_pending_credits(exo_pending)} exobiology as lost."

def plugin_prefs(parent:tk.Widget, cmdr:str, is_beta:bool) -> tk.Widget:
    """ Return a TK Frame for adding to the EDMC settings dialog. """
    overlay_available:bool = Context.overlay_backend is not None and Context.overlay_backend.available
    return prefs_ui.build_prefs(parent, cmdr, is_beta, overlay_available, VERSION, _clear_unsold_data)

def prefs_changed(cmdr:str, is_beta:bool) -> None:
    """ Save settings. """
    prefs_ui.save_prefs(cmdr, is_beta)

def _apply_flags(flags:dict) -> None:
    if flags.get("panel") and Context.panel is not None:
        Context.panel.refresh()
    if flags.get("panel") and Context.history_view is not None:
        Context.history_view.refresh() # cheap no-op if the popup isn't open
    if flags.get("overlay") and Context.store is not None:
        if Context.radar is not None:
            Context.radar.render(Context.store, explorer_state)
        if Context.summary_overlay is not None:
            Context.summary_overlay.render(Context.store, explorer_state) # same trigger as radar, steady dashboard-tick cadence

def journal_entry(cmdr:str, is_beta:bool, system:str, station:str, entry:dict, state:dict) -> None:
    """ Handle journal events """
    if Context.store is None:
        return
    _apply_flags(dispatch(Context.store, explorer_state, cmdr, entry, state))

def dashboard_entry(cmdr:str, is_beta:bool, entry:dict) -> None:
    """ Handle dashboard and state changes. """
    _apply_flags(on_dashboard_entry(explorer_state, entry))
