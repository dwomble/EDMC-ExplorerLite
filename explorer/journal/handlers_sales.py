"""
Cartography sale handlers: SellExplorationData (older/legacy form) and MultiSellExplorationData
(current, since 3.3) -- actual credits earned, ground truth. Only system-level totals are
available (no per-body breakdown), so per-body "actual" value is never tracked, only the
Cmdr-level running total plus this raw sale-event log.
"""
import json

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.util import now_iso

def on_sell_exploration_data(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.cmdr_id is None:
        return {}
    total = entry.get("TotalEarnings")
    if total is None:
        total = entry.get("BaseValue", 0) + entry.get("Bonus", 0)
    if not total:
        return {}

    now = now_iso()
    store.record_sale(state.cmdr_id, "cartography", now, state.system_name or None, total, json.dumps(entry))

    for item in entry.get("Discovered", []):
        system_name = item.get("SystemName")
        if system_name:
            store.mark_system_sold(state.cmdr_id, system_name, now)

    return {"panel": True}
