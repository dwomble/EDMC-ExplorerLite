""" Surface mining prediction: ground type (planet class + volcanism) to likely commodities, from data/mining_rates.json. """
import json
import re
import unicodedata
from pathlib import Path

_DATA:dict = json.loads((Path(__file__).resolve().parent.parent.parent / 'data' / 'mining_rates.json').read_text())
GROUNDS:dict[str, dict] = _DATA['grounds']

_ROCKY_VOLCANISM:tuple[tuple[str, str], ...] = (
    ('metallic magma', 'rocky metallic magma'), ('rocky magma', 'rocky rocky magma'), ('silicate vapour', 'rocky silicate vapour'),
)
_CLASSES:dict[str, str] = {
    'Icy body': 'icy', 'Rocky ice body': 'rocky ice', 'High metal content body': 'high metal content', 'Metal rich body': 'metal rich',
}

ALIASES:dict[str, str] = {
    'lowtemperaturediamonds': 'lowtempdiamonds', 'ltd': 'lowtempdiamonds', 'ltds': 'lowtempdiamonds',
    'methanol': 'methanolmonohydratecrystals', 'methanolmonohydrate': 'methanolmonohydratecrystals',
    'hematite': 'haematite', 'sulfur': 'sulphur',
}

def norm(name:str) -> str:
    """ Case, accent, space and punctuation-insensitive key, alias-resolved (Bastnäsite, Helium 3, LTD). """
    key:str = re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower())
    return ALIASES.get(key, key)

def parse_watch(csv:str) -> set[str]:
    """ Comma-separated pref text into a set of norm() keys. """
    return {norm(s) for s in csv.split(',') if s.strip()}

def ground_type(planet_class:str|None, volcanism:str|None) -> str|None:
    """ Ground key for a landable body, or None if it has no surveyed ground. """
    if planet_class in _CLASSES: return _CLASSES[planet_class]
    if planet_class != 'Rocky body': return None

    for keyword, ground in _ROCKY_VOLCANISM:
        if keyword in (volcanism or ''): return ground

    return 'rocky none'

def watched_rates(planet_class:str|None, volcanism:str|None, watched:set[str]) -> list[tuple[str, float]]:
    """ (commodity, pct) for watched commodities on this ground, best first. """
    ground:dict|None = GROUNDS.get(ground_type(planet_class, volcanism) or '')
    if not ground: return []

    hits:list[tuple[str, float]] = [(name, pct) for name, pct in ground['rates'].items() if norm(name) in watched]
    return sorted(hits, key=lambda h: -h[1])
