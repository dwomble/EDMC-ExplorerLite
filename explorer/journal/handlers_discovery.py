"""
Honk-stage handlers: FSSDiscoveryScan (the honk) and FSSAllBodiesFound.
"""
from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.valuation import cartography, honk_heuristic

def on_honk(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None:
        return {}
    body_count:int = entry.get("BodyCount", 0)
    non_body_count:int = entry.get("NonBodyCount", 0)
    verdict:str = honk_heuristic.assess(body_count, non_body_count)

    # The arrival star's AutoScan fires automatically on jump-in, well before the player
    # manually triggers the honk -- so its star_type is normally already known here. A neutron
    # star/white dwarf/black hole is worth a full scan regardless of how few bodies the honk
    # itself reports (real regression: a 3-body neutron star system read as "done").
    if verdict != "worth a full scan" and any(
        body["body_type"] == "Star" and cartography.is_exotic_star_type(body["star_type"] or "")
        for body in store.get_bodies_for_system(state.system_id)
    ):
        verdict = "worth a full scan"

    store.update_system(state.system_id, honk_body_count=body_count, honk_non_body_count=non_body_count, honk_hint=verdict)
    return {"panel": True}

def on_all_bodies_found(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None:
        return {}
    store.update_system(state.system_id, all_bodies_found=1, fss_body_count=entry.get("Count", 0))
    return {"panel": True}
