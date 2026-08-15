""" Predicts which genera/species could plausibly be present on a body from its Scan (Detailed)
fields alone, pre-DSS. Categorical fields are hard gates; temperature/gravity/pressure taper
confidence toward a ruleset's edge rather than hard-failing. Confidence is the best (max) score
across a genus/species's matching rulesets. predict_species() returns [] for a genus outside
SPECIES_RULESETS -- callers fall back to predict_genera()'s genus-only guess. """
from explorer.valuation.genus_conditions import GENUS_RULESETS, Ruleset
from explorer.valuation.species_conditions import SPECIES_RULESETS

RANGE_BUFFER_FRAC:float = 0.15 # how far outside a documented temp/gravity/pressure edge confidence tapers to 0

GRAVITY_MS2_PER_G:float = 9.797759 # matches the reference source's own constant, not the textbook 9.80665
PRESSURE_PA_PER_ATM:float = 101231.656250 # ditto, for SurfacePressure -> the reference's pressure unit

def _range_confidence(value:float, low:float|None, high:float|None, buffer_frac:float = RANGE_BUFFER_FRAC) -> float:
    """ 1.0 inside [low, high] (either bound optional/unconstrained); tapers linearly to 0.0
    over a margin beyond whichever edge is exceeded. """
    if low is not None and value < low:
        span:float = (high - low) if (high is not None) else max(abs(low), 1.0)
        overshoot:float = low - value
    elif high is not None and value > high:
        span:float = (high - low) if (low is not None) else max(abs(high), 1.0)
        overshoot:float = value - high
    else:
        return 1.0
    buffer:float = span * buffer_frac
    return 0.0 if overshoot >= buffer else 1.0 - (overshoot / buffer)

def _volcanism_matches(spec:str|set[str]|None, volcanism:str) -> bool:
    if spec is None:
        return True
    has_volcanism:bool = bool(volcanism.strip())
    if spec == 'any':
        return has_volcanism
    if spec == 'none':
        return not has_volcanism
    return any(keyword in volcanism for keyword in spec)

def _hard_gates_pass(rs:Ruleset, star_type:str|None, planet_class:str, atmosphere_type:str, volcanism:str) -> bool:
    if rs.atmosphere is not None and atmosphere_type not in rs.atmosphere:
        return False
    if rs.body_types is not None and planet_class not in rs.body_types:
        return False
    if rs.star_types is not None and star_type is not None and star_type not in rs.star_types:
        return False
    return _volcanism_matches(rs.volcanism, volcanism)

def _ruleset_confidence(rs:Ruleset, temp_k:float|None, gravity_g:float|None, pressure_atm:float|None) -> float:
    confidences:list[float] = []
    if temp_k is not None and (rs.min_temp_k is not None or rs.max_temp_k is not None):
        confidences.append(_range_confidence(temp_k, rs.min_temp_k, rs.max_temp_k))
    if gravity_g is not None and (rs.min_gravity_g is not None or rs.max_gravity_g is not None):
        confidences.append(_range_confidence(gravity_g, rs.min_gravity_g, rs.max_gravity_g))
    if pressure_atm is not None and (rs.min_pressure_atm is not None or rs.max_pressure_atm is not None):
        confidences.append(_range_confidence(pressure_atm, rs.min_pressure_atm, rs.max_pressure_atm))
    return min(confidences) if confidences else 1.0

def _parse_entry_conditions(entry:dict) -> tuple[str, str, str, float|None, float|None, float|None]:
    """ (planet_class, atmosphere_type, volcanism, temp_k, gravity_g, pressure_atm) from a raw
    Scan (Detailed) journal entry -- shared by predict_genera() and predict_species() so both
    read the same fields the same way. """
    planet_class:str = entry.get("PlanetClass", "")
    atmosphere_type:str = entry.get("AtmosphereType", "None")
    volcanism:str = entry.get("Volcanism") or ""

    temp_k:float|None = entry.get("SurfaceTemperature")
    if not isinstance(temp_k, (int, float)):
        temp_k = None

    gravity_raw:float|None = entry.get("SurfaceGravity")
    gravity_g:float|None = gravity_raw / GRAVITY_MS2_PER_G if isinstance(gravity_raw, (int, float)) else None

    pressure_raw:float|None = entry.get("SurfacePressure")
    pressure_atm:float|None = pressure_raw / PRESSURE_PA_PER_ATM if isinstance(pressure_raw, (int, float)) else None

    return planet_class, atmosphere_type, volcanism, temp_k, gravity_g, pressure_atm

def _best_ruleset_score(
    rulesets:list[Ruleset], star_type:str|None, planet_class:str, atmosphere_type:str, volcanism:str,
    temp_k:float|None, gravity_g:float|None, pressure_atm:float|None,
) -> float|None:
    """ Best (max) confidence across `rulesets` that pass their hard gates, or None if none do. """
    best:float|None = None
    for rs in rulesets:
        if not _hard_gates_pass(rs, star_type, planet_class, atmosphere_type, volcanism):
            continue
        score:float = _ruleset_confidence(rs, temp_k, gravity_g, pressure_atm)
        if score > 0.0 and (best is None or score > best):
            best = score
    return best

def predict_genera(entry:dict, nearest_star_type:str|None) -> list[tuple[str, float]]:
    """ (genus, confidence 0.0-1.0) for every genus with at least one matching ruleset, sorted
    by confidence desc. """
    planet_class, atmosphere_type, volcanism, temp_k, gravity_g, pressure_atm = _parse_entry_conditions(entry)

    results:list[tuple[str, float]] = []
    for genus, rulesets in GENUS_RULESETS.items():
        best:float|None = _best_ruleset_score(
            rulesets, nearest_star_type, planet_class, atmosphere_type, volcanism, temp_k, gravity_g, pressure_atm
        )
        if best is not None:
            results.append((genus, best))

    results.sort(key=lambda pair: pair[1], reverse=True)
    return results

def predict_species(genus:str, entry:dict, nearest_star_type:str|None) -> list[tuple[str, float]]:
    """ (species, confidence 0.0-1.0) for every species of `genus` with at least one matching
    ruleset in SPECIES_RULESETS, sorted by confidence desc. Empty if `genus` isn't covered by
    SPECIES_RULESETS at all -- callers should fall back to predict_genera()'s genus-only guess
    in that case, not treat an empty list as "no biology possible". """
    rulesets_by_species:dict[str, list[Ruleset]]|None = SPECIES_RULESETS.get(genus)
    if not rulesets_by_species:
        return []

    planet_class, atmosphere_type, volcanism, temp_k, gravity_g, pressure_atm = _parse_entry_conditions(entry)

    results:list[tuple[str, float]] = []
    for species, rulesets in rulesets_by_species.items():
        best:float|None = _best_ruleset_score(
            rulesets, nearest_star_type, planet_class, atmosphere_type, volcanism, temp_k, gravity_g, pressure_atm
        )
        if best is not None:
            results.append((species, best))

    results.sort(key=lambda pair: pair[1], reverse=True)
    return results
