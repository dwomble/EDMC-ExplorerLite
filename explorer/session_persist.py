"""
Tiny JSON snapshot of "where we are right now" (system/body) -- lets an EDMC-only restart
(game still running) resume mid-body instead of going blank until the next journal event,
since EDMC does not replay journal history to plugins on startup. Bridges state.py's
in-memory context only; actual scan progress/values already survive via db/store.py.
"""
import json
from pathlib import Path

from config import config # type: ignore

from explorer.constants import GH_PROJECT

SESSION_FILENAME:str = "session_state.json"

def resolve_session_path() -> Path:
    directory:Path = Path(config.app_dir_path) / GH_PROJECT / "data"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / SESSION_FILENAME

def save(cmdr:str, system_address:int|None, system_name:str, body_id:int|None, body_name:str) -> None:
    resolve_session_path().write_text(json.dumps({
        "cmdr": cmdr,
        "system_address": system_address,
        "system_name": system_name,
        "body_id": body_id,
        "body_name": body_name,
    }))

def load() -> dict|None:
    try:
        return json.loads(resolve_session_path().read_text())
    except (OSError, json.JSONDecodeError):
        return None
