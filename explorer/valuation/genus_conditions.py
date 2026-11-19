""" Spawn conditions per genus, for genus_prediction.py's pre-DSS estimate (data in
data/genus_rulesets.json). A genus matches via ANY ONE ruleset (OR'd); within a ruleset every
present field must match (AND'd). Own values, MIT; cross-checked against Silarn/EDMC-BioScan
(GPLv2) as reference only.

Ruleset fields: atmosphere/body_types/star_types are None (unconstrained) or a hard-gate set
("None" is a valid atmosphere member, for airless bodies); gravity/temp/pressure min/max are
soft bounds (see genus_prediction.py's tapering); volcanism is None/'any'/'none'/a keyword set;
unmodeled is True when the JSON entry carries an "unmodeled" reason. """
import json
from dataclasses import dataclass
from pathlib import Path

_DATA_DIR:Path = Path(__file__).resolve().parent.parent.parent / 'data' # repo/plugin root's data/

@dataclass
class Ruleset:
    atmosphere:set[str]|None
    body_types:set[str]|None
    star_types:set[str]|None
    min_gravity_g:float|None
    max_gravity_g:float|None
    min_temp_k:float|None
    max_temp_k:float|None
    min_pressure_atm:float|None
    max_pressure_atm:float|None
    volcanism:str|set[str]|None # None, 'any', 'none', or a set of substring keywords
    unmodeled:bool = False

def ruleset_from_json(entry:dict) -> Ruleset:
    """ One JSON ruleset object (missing keys = unconstrained) into a Ruleset. """
    as_set = lambda v: set(v) if isinstance(v, list) else v
    return Ruleset(
        atmosphere=as_set(entry.get('atmosphere')), body_types=as_set(entry.get('body_types')),
        star_types=as_set(entry.get('star_types')), min_gravity_g=entry.get('min_gravity_g'),
        max_gravity_g=entry.get('max_gravity_g'), min_temp_k=entry.get('min_temp_k'),
        max_temp_k=entry.get('max_temp_k'), min_pressure_atm=entry.get('min_pressure_atm'),
        max_pressure_atm=entry.get('max_pressure_atm'), volcanism=as_set(entry.get('volcanism')),
        unmodeled='unmodeled' in entry,
    )

def rulesets_from_json(entries:list[dict]) -> list[Ruleset]:
    return [ruleset_from_json(e) for e in entries]

def load_json(filename:str) -> dict:
    return json.loads((_DATA_DIR / filename).read_text())

GENUS_RULESETS:dict[str, list[Ruleset]] = {
    genus: rulesets_from_json(entries) for genus, entries in load_json('genus_rulesets.json').items()
}
