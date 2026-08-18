"""
Context/state-tracking handlers: no direct valuation, just "where are we right now" so the
body/exobiology-specific handlers know what they're looking at.
"""
from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer import session_persist

def _persist(state:ExplorerState) -> None:
    session_persist.save(state.cmdr, state.system_address, state.system_name, state.body_id, state.body_name)

def _restore_sample_positions(store:ExplorerStore, state:ExplorerState) -> None:
    """ Reloads this visit's radar samples on restart. """
    if state.cmdr_id is None or state.system_id is None or state.body_id is None:
        return
    body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, state.body_id, state.body_name)
    for row in store.get_sample_positions_for_body(body_pk):
        state.sample_positions.setdefault(row["genus"], []).append((row["latitude"], row["longitude"], None))
        state.current_genus = row["genus"] # last row wins, insertion-ordered

def restore_last_session(store:ExplorerStore, state:ExplorerState) -> None:
    """ Called once at plugin startup, before any journal event arrives, so the panel doesn't
    sit at "Explorer -- idle" until the next live event. enter_system()'s cold-start check
    corrects anything actually different once a real Location/FSDJump arrives. """
    saved:dict|None = session_persist.load()
    if not saved:
        return
    cmdr:str|None = saved.get("cmdr")
    system_address:int|None = saved.get("system_address")
    if not cmdr or system_address is None:
        return

    state.cmdr = cmdr
    state.cmdr_id = store.get_or_create_cmdr(cmdr)
    state.system_address = system_address
    state.system_name = saved.get("system_name") or ""
    state.system_id = store.get_or_create_system(state.cmdr_id, system_address, state.system_name)
    state.body_id = saved.get("body_id")
    state.body_name = saved.get("body_name") or ""
    state.restored_at_startup = True

def on_load_game(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.reset_body()
    if not state.restored_at_startup: # don't overwrite the still-unconfirmed resumable snapshot on disk
        _persist(state)
    return {"panel": True}

def on_continued(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    return {}

def enter_system(store:ExplorerStore, state:ExplorerState, edmc_state:dict) -> dict:
    """ Called by dispatch() for Location/FSDJump/CarrierJump -- reads SystemAddress/SystemName
    from EDMC's own state dict rather than re-parsing the journal entry. On a cold start (no
    system_id yet, or restore_last_session() pre-populated one), resumes the last known body
    if it's the same Cmdr/system rather than going blank until the next event. """
    system_address:int|None = edmc_state.get("SystemAddress")
    if system_address is None:
        return {}

    cold_start:bool = state.system_id is None or state.restored_at_startup
    state.restored_at_startup = False
    saved:dict|None = session_persist.load() if cold_start else None

    state.system_address = system_address
    state.system_name = edmc_state.get("SystemName") or ""
    state.nearest_star_type = None
    state.last_bio_body_id = None
    state.last_bio_body_name = ""
    state.reset_body()
    if state.cmdr_id is not None:
        state.system_id = store.get_or_create_system(state.cmdr_id, system_address, state.system_name)

    if saved and saved.get("cmdr") == state.cmdr and saved.get("system_address") == system_address:
        state.body_id = saved.get("body_id")
        state.body_name = saved.get("body_name") or ""
        _restore_sample_positions(store, state)

    _persist(state)
    return {"panel": True, "overlay": "radar"}

def on_start_jump(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.reset_body()
    _persist(state)
    return {}

def on_approach_body(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.body_id = entry.get("BodyID")
    state.body_name = entry.get("Body", "")
    _persist(state)
    return {"panel": True, "overlay": "radar"}

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
    _persist(state)
    return {"panel": True, "overlay": "radar"}

def on_leave_body(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    state.reset_body()
    _persist(state)
    return {"panel": True, "overlay": "radar"}

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
