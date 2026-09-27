"""
Cartography sale handlers: SellExplorationData/MultiSellExplorationData (actual credits earned,
ground truth) -- only system-level totals exist, so per-body "actual" is never tracked, just
the Cmdr-level running total. Also Died: any unsold cartography/exobiology data is lost when
the ship is destroyed, per the game's own rules.
"""
import json

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.util import now_iso

def on_sell_exploration_data(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.cmdr_id is None:
        return {}
    # TotalEarnings can be a real 0 despite a nonzero sale -- a confirmed Frontier journal quirk.
    total:int = entry.get("TotalEarnings") or entry.get("BaseValue", 0) + entry.get("Bonus", 0)
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
    store.mark_unsold_species_lost(cmdr_id, timestamp)

def on_died(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.cmdr_id is None:
        return {}
    mark_everything_unsold_lost(store, state.cmdr_id, now_iso())
    return {"panel": True}
