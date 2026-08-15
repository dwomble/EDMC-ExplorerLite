import math
from datetime import datetime, timezone

def now_iso() -> str:
    """ Current UTC time as an ISO-8601 string, for DB timestamp columns. """
    return datetime.now(timezone.utc).isoformat()

def local_offset_m(lat0:float, lon0:float, lat:float, lon:float, planet_radius_m:float) -> tuple[float, float]:
    """ Flat-earth approximation, meters east/north from (lat0, lon0) -- fine at the scale of exobiology sample distances. """
    y:float = math.radians(lat - lat0) * planet_radius_m
    x:float = math.radians(lon - lon0) * planet_radius_m * math.cos(math.radians(lat0))
    return x, y

def surface_distance_m(lat0:float, lon0:float, lat:float, lon:float, planet_radius_m:float) -> float:
    x, y = local_offset_m(lat0, lon0, lat, lon, planet_radius_m)
    return math.hypot(x, y)
