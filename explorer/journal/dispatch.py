"""
Journal event dispatch: a flat dict[event_name, handler], structurally like EDR's
edrjournalhandler.py dispatch table (not copied code -- our own, much smaller map).

Each handler takes (store, state, entry) and returns a small "what changed" flag dict (e.g.
{"panel": True}) so load.py's journal_entry can decide whether to refresh the panel/overlay
without every handler needing UI imports. System-entry events (SYSTEM_ENTRY_EVENTS) are
special-cased straight to handlers_context.enter_system() instead, since that one needs EDMC's
own state dict rather than the raw journal entry.
"""
from typing import Callable

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_context, handlers_discovery, handlers_bodies, handlers_exobiology, handlers_sales

SYSTEM_ENTRY_EVENTS:frozenset[str] = frozenset({"Location", "FSDJump", "CarrierJump"})

EVENT_HANDLERS:dict[str, Callable] = {
    "LoadGame": handlers_context.on_load_game,
    "Continued": handlers_context.on_continued,
    "StartJump": handlers_context.on_start_jump,
    "ApproachBody": handlers_context.on_approach_body,
    "SupercruiseExit": handlers_context.on_supercruise_exit,
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

def dispatch(store:ExplorerStore, state:ExplorerState, cmdr:str, entry:dict, edmc_state:dict) -> dict:
    """ Route one journal entry to its handler, if any. Returns a "what changed" flag dict.
    `edmc_state` is EDMC's own per-Cmdr state dict (see PLUGINS.md) -- already updated for this
    entry, so system-entry events read SystemAddress/SystemName from it rather than re-parsing
    the journal entry ourselves. """
    if cmdr and cmdr != state.cmdr:
        state.cmdr = cmdr
        state.cmdr_id = None # force re-resolution below for the new Cmdr
    if state.cmdr_id is None and state.cmdr:
        state.cmdr_id = store.get_or_create_cmdr(state.cmdr)

    event:str = entry.get("event", "")
    if event in SYSTEM_ENTRY_EVENTS:
        return handlers_context.enter_system(store, state, edmc_state)

    handler:Callable|None = EVENT_HANDLERS.get(event)
    if handler is None:
        return {}
    return handler(store, state, entry) or {}
