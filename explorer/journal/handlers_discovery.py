"""
Honk-stage handlers: FSSDiscoveryScan (the honk) and FSSAllBodiesFound.
"""
from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.valuation import honk_heuristic

def on_honk(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None:
        return {}
    body_count:int = entry.get("BodyCount", 0)
    non_body_count:int = entry.get("NonBodyCount", 0)

    # star's AutoScan usually fires before the honk
    star_types:list[str] = [
        body["star_type"] or "" for body in store.get_bodies_for_system(state.system_id) if body["body_type"] == "Star"
    ]
    verdict:str = honk_heuristic.assess(body_count, star_types)

    store.update_system(state.system_id, honk_body_count=body_count, honk_non_body_count=non_body_count, honk_hint=verdict)
    return {"panel": True}

def on_all_bodies_found(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None:
        return {}
    store.update_system(state.system_id, all_bodies_found=1, fss_body_count=entry.get("Count", 0))
    return {"panel": True}
