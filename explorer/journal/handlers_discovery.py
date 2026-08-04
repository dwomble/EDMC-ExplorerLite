"""
Honk-stage handlers: FSSDiscoveryScan (the honk) and FSSAllBodiesFound.
"""
from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.valuation import honk_heuristic

def on_honk(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None:
        return {}
    body_count = entry.get("BodyCount", 0)
    non_body_count = entry.get("NonBodyCount", 0)
    verdict = honk_heuristic.assess(body_count, non_body_count)
    store.update_system(state.system_id, honk_body_count=body_count, honk_non_body_count=non_body_count, honk_hint=verdict)
    return {"panel": True}

def on_all_bodies_found(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None:
        return {}
    store.update_system(state.system_id, all_bodies_found=1, fss_body_count=entry.get("Count", 0))
    return {"panel": True}
