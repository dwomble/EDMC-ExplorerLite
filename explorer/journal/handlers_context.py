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

def _enter_system(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    system_address:int|None = entry.get("SystemAddress")
    if system_address is None:
        return {}
    state.system_address = system_address
    state.system_name = entry.get("StarSystem", "")
    state.nearest_star_type = None
    state.reset_body()
    if state.cmdr_id is not None:
        state.system_id = store.get_or_create_system(state.cmdr_id, system_address, state.system_name)
    return {"panel": True}

def on_location(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    return _enter_system(store, state, entry)

def on_fsd_jump(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    return _enter_system(store, state, entry)

def on_start_jump(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.reset_body()
    return {}

def on_approach_body(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.body_id = entry.get("BodyID")
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
