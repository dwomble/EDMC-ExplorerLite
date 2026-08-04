"""
Journal event dispatch: a flat dict[event_name, handler], structurally like EDR's
edrjournalhandler.py dispatch table (not copied code -- our own, much smaller map).

Each handler takes (store, state, entry) and returns a small "what changed" flag dict (e.g.
{"panel": True}) so load.py's journal_entry can decide whether to refresh the panel/overlay
without every handler needing UI imports.
"""
from typing import Callable

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_context, handlers_discovery, handlers_bodies, handlers_exobiology, handlers_sales

EVENT_HANDLERS:dict[str, Callable] = {
    "LoadGame": handlers_context.on_load_game,
    "Continued": handlers_context.on_continued,
    "Location": handlers_context.on_location,
    "FSDJump": handlers_context.on_fsd_jump,
    "CarrierJump": handlers_context.on_fsd_jump,
    "StartJump": handlers_context.on_start_jump,
    "ApproachBody": handlers_context.on_approach_body,
    "LeaveBody": handlers_context.on_leave_body,
    "Touchdown": handlers_context.on_touchdown,
    "Liftoff": handlers_context.on_liftoff,

    "FSSDiscoveryScan": handlers_discovery.on_honk,
    "FSSAllBodiesFound": handlers_discovery.on_all_bodies_found,

    "FSSBodySignals": handlers_bodies.on_fss_body_signals,
    "Scan": handlers_bodies.on_scan,
    "SAAScanComplete": handlers_bodies.on_saa_scan_complete,
    "SAASignalsFound": handlers_bodies.on_saa_signals_found,

    "ScanOrganic": handlers_exobiology.on_scan_organic,
    "SellOrganicData": handlers_exobiology.on_sell_organic_data,

    "SellExplorationData": handlers_sales.on_sell_exploration_data,
    "MultiSellExplorationData": handlers_sales.on_sell_exploration_data,
}

def dispatch(store:ExplorerStore, state:ExplorerState, cmdr:str, entry:dict) -> dict:
    """ Route one journal entry to its handler, if any. Returns a "what changed" flag dict. """
    if cmdr and cmdr != state.cmdr:
        state.cmdr = cmdr
        state.cmdr_id = None # force re-resolution below for the new Cmdr
    if state.cmdr_id is None and state.cmdr:
        state.cmdr_id = store.get_or_create_cmdr(state.cmdr)

    handler:Callable|None = EVENT_HANDLERS.get(entry.get("event", ""))
    if handler is None:
        return {}
    return handler(store, state, entry) or {}
