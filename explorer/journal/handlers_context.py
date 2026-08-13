"""
Context/state-tracking handlers: no direct valuation, just "where are we right now" so the
body/exobiology-specific handlers know what they're looking at.
"""
from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState

def on_load_game(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.reset_body()
    return {"panel": True}

def on_continued(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    return {}

def enter_system(store:ExplorerStore, state:ExplorerState, edmc_state:dict) -> dict:
    """ Called by dispatch() for Location/FSDJump/CarrierJump -- reads SystemAddress/SystemName
    from EDMC's own state dict (already updated for this entry) rather than re-parsing the
    journal entry ourselves, since EDMC tracks the exact same fields from the exact same events. """
    system_address:int|None = edmc_state.get("SystemAddress")
    if system_address is None:
        return {}
    state.system_address = system_address
    state.system_name = edmc_state.get("SystemName") or ""
    state.nearest_star_type = None
    state.reset_body()
    if state.cmdr_id is not None:
        state.system_id = store.get_or_create_system(state.cmdr_id, system_address, state.system_name)
    return {"panel": True}

def on_start_jump(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.reset_body()
    return {}

def on_approach_body(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.body_id = entry.get("BodyID")
    state.body_name = entry.get("Body", "")
    return {"panel": True}

def on_supercruise_exit(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    """ Dropping out of supercruise near a body -- often the first real look at a body's
    specifics, well before ApproachBody/Touchdown. Skip station drops (BodyType "Station"). """
    if entry.get("BodyType") == "Station":
        return {}
    body_id:int|None = entry.get("BodyID")
    if body_id is None:
        return {}
    state.body_id = body_id
    state.body_name = entry.get("Body", "")
    return {"panel": True}

def on_leave_body(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.reset_body()
    return {"panel": True}

def on_touchdown(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.body_id = entry.get("BodyID", state.body_id)
    state.body_name = entry.get("Body", state.body_name)
    state.landed = True
    if "Latitude" in entry:
        state.has_lat_long = True
        state.latitude = entry.get("Latitude")
        state.longitude = entry.get("Longitude")
    return {"panel": True, "overlay": "radar"}

def on_liftoff(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.landed = False
    return {"panel": True, "overlay": "radar"}
