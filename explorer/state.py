"""
In-memory session state: "where are we right now" -- current Cmdr/system/body/surface
context, plus the live position data the overlay radar needs. No DB writes happen here;
journal/dashboard handlers read and update this directly.
"""
from dataclasses import dataclass, field

@dataclass
class ExplorerState:
    cmdr:str = ""
    cmdr_id:int|None = None # DB PK, resolved/cached by journal/dispatch.py each dispatch call

    system_address:int|None = None
    system_name:str = ""
    system_id:int|None = None # DB PK for the current system, refreshed on system-change events
    nearest_star_type:str|None = None # most recently Scan'd star this system -- a proxy for genus_prediction.py

    restored_at_startup:bool = False # set by restore_last_session(); makes enter_system() treat the
    # next real system-entry event as a cold start even though system_id is already populated

    body_id:int|None = None
    body_name:str = ""

    landed:bool = False
    on_foot:bool = False # from Status.json (dashboard.py), not EDMC's journal-derived state['OnFoot'] --
    # more immediate, and EDMC's own docs admit theirs "might not set this 100% correctly"
    has_lat_long:bool = False

    latitude:float|None = None
    longitude:float|None = None
    heading:float|None = None
    altitude:float|None = None
    planet_radius:float|None = None

    # Session-only, keyed by genus: (lat, lon, color_name) per sample/tag for the radar's markers.
    # color_name is the tag's variant color, or None for a real sample. Cleared on reset_body().
    sample_positions:dict[str, list[tuple[float, float, str|None]]] = field(default_factory=dict)

    current_genus:str|None = None # genus of the most recent real sample -- the radar's one active ring

    def reset_body(self) -> None:
        """ Called on leaving a body / jumping system -- clears body-scoped context. """
        self.body_id = None
        self.body_name = ""
        self.landed = False
        self.has_lat_long = False
        self.latitude = None
        self.longitude = None
        self.heading = None
        self.altitude = None
        self.planet_radius = None
        self.sample_positions = {}
        self.current_genus = None

    @property
    def exobiology_relevant(self) -> bool:
        """ Whether the on-body exobiology UI/overlay section is currently relevant. """
        return self.landed and self.on_foot and self.body_id is not None

    def reset_all(self) -> None:
        """ Fresh-session reset -- for tests, which reuse this module-level singleton and need real isolation. """
        self.__dict__.update(ExplorerState().__dict__)

state = ExplorerState()
