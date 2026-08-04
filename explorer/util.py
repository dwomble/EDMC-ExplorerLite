from datetime import datetime, timezone

def now_iso() -> str:
    """ Current UTC time as an ISO-8601 string, for DB timestamp columns. """
    return datetime.now(timezone.utc).isoformat()
