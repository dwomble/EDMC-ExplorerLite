"""
dashboard_entry handler: Status.json updates. Feeds the overlay radar's live position
(Latitude/Longitude/Heading/Altitude) and general context-sensitivity (on-foot, landed) --
no DB writes here, purely live state.
"""
from edmc_data import FlagsLanded, FlagsHasLatLong, Flags2OnFoot # type: ignore

from explorer.state import ExplorerState

# Tracks whether the exobiology section was showing on the last tick, so the panel only
# rebuilds on an actual transition (e.g. landing/lifting off) rather than every ~1s dashboard
# tick -- the overlay radar still gets a flag every tick, since it needs live position.
_last_exobiology_relevant:bool|None = None

def on_dashboard_entry(state:ExplorerState, entry:dict) -> dict:
    global _last_exobiology_relevant

    flags:int = entry.get("Flags", 0)
    flags2:int = entry.get("Flags2", 0)

    state.landed = bool(flags & FlagsLanded)
    state.on_foot = bool(flags2 & Flags2OnFoot)
    state.has_lat_long = bool(flags & FlagsHasLatLong)

    if state.has_lat_long:
        state.latitude = entry.get("Latitude")
        state.longitude = entry.get("Longitude")
        state.heading = entry.get("Heading")
        state.altitude = entry.get("Altitude")
        state.planet_radius = entry.get("PlanetRadius")

    relevant:bool = state.exobiology_relevant
    result:dict[str, bool|str] = {"overlay": "radar"} # every tick -- render()'s own guards decide whether to actually draw
    if relevant != _last_exobiology_relevant:
        _last_exobiology_relevant = relevant
        result["panel"] = True
    return result
