"""
Cartography sale handlers: SellExplorationData (older/legacy form) and MultiSellExplorationData
(current, since 3.3) -- actual credits earned, ground truth. Only system-level totals are
available (no per-body breakdown), so per-body "actual" value is never tracked, only the
Cmdr-level running total plus this raw sale-event log.

Also Died -- the inverse of a sale: any cartography or completed exobiology data still held
unsold is lost when the ship is destroyed, per the game's own rules.
"""
import json

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.util import now_iso

def on_sell_exploration_data(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.cmdr_id is None:
        return {}
    total:int|None = entry.get("TotalEarnings")
    if total is None:
        total = entry.get("BaseValue", 0) + entry.get("Bonus", 0)
    if not total:
        return {}

    now:str = now_iso()
    store.record_sale(state.cmdr_id, "cartography", now, state.system_name or None, total, json.dumps(entry))

    for item in entry.get("Discovered", []):
        system_name:str|None = item.get("SystemName")
        if system_name:
            store.mark_system_sold(state.cmdr_id, system_name, now)

    return {"panel": True}

def mark_everything_unsold_lost(store:ExplorerStore, cmdr_id:int, timestamp:str) -> None:
    """ Shared by on_died() and the manual-clear action. """
    store.mark_all_unsold_systems_lost(cmdr_id, timestamp)
    store.mark_all_unsold_species_progress_lost(cmdr_id, timestamp)

def on_died(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.cmdr_id is None:
        return {}
    mark_everything_unsold_lost(store, state.cmdr_id, now_iso())
    return {"panel": True}
