"""
Predicts which genera could plausibly be present on a body from its Scan (Detailed) journal
fields alone -- before a DSS/SAASignalsFound reveals the real answer. Reads the raw entry dict
directly (same convention as valuation/cartography.py), not a typed wrapper.

Categorical conditions (star type, planet class, atmosphere type, volcanism) are hard gates --
a body outside a genus's known set excludes that genus outright, not a low score. Temperature
and gravity are soft: confidence tapers from 1.0 inside the documented range down to 0.0 over a
margin beyond either edge, since a finite sample of real sightings can't rule out a slightly
wider true range -- a near-miss should read as lower confidence, not an identical hard fail.
"""
from explorer.valuation.genus_conditions import GENUS_CONDITIONS, GenusConditions

RANGE_BUFFER_FRAC:float = 0.15 # how far outside a documented temp/gravity edge confidence tapers to 0

GRAVITY_MS2_PER_G:float = 9.80665

def _range_confidence(value:float, low:float, high:float, buffer_frac:float = RANGE_BUFFER_FRAC) -> float:
    """ 1.0 inside [low, high]; tapers linearly to 0.0 over a margin beyond either edge. """
    if low <= value <= high:
        return 1.0
    span:float = high - low
    buffer:float = span * buffer_frac if span > 0 else max(abs(high), 1.0) * buffer_frac
    overshoot:float = (low - value) if value < low else (value - high)
    if overshoot >= buffer:
        return 0.0
    return 1.0 - (overshoot / buffer)

def _score_genus(conditions:GenusConditions, star_type:str|None, planet_class:str, atmosphere_type:str,
                  has_volcanism:bool, temp_k:float|None, gravity_g:float|None) -> float|None:
    """ None = hard-excluded; otherwise a 0.0-1.0 confidence. """
    if conditions.star_types is not None and star_type is not None and star_type not in conditions.star_types:
        return None
    if conditions.planet_classes is not None and planet_class not in conditions.planet_classes:
        return None
    if conditions.atmosphere_types is not None:
        required:set[str] = conditions.atmosphere_types or {"None"}
        if atmosphere_type not in required:
            return None
    if conditions.volcanism_required is not None and conditions.volcanism_required != has_volcanism:
        return None

    confidences:list[float] = []
    if conditions.temp_range_k is not None and temp_k is not None:
        confidences.append(_range_confidence(temp_k, *conditions.temp_range_k))
    if conditions.max_gravity_g is not None and gravity_g is not None:
        confidences.append(_range_confidence(gravity_g, 0.0, conditions.max_gravity_g))
    if not confidences:
        return 1.0
    score:float = min(confidences)
    return score if score > 0.0 else None

def predict_genera(entry:dict, nearest_star_type:str|None) -> list[tuple[str, float]]:
    """ (genus, confidence 0.0-1.0) for every genus not hard-excluded, sorted by confidence desc. """
    planet_class:str = entry.get("PlanetClass", "")
    atmosphere_type:str = entry.get("AtmosphereType", "None")
    has_volcanism:bool = bool((entry.get("Volcanism") or "").strip())

    temp_k:float|None = entry.get("SurfaceTemperature")
    gravity_raw:float|None = entry.get("SurfaceGravity")
    gravity_g:float|None = gravity_raw / GRAVITY_MS2_PER_G if isinstance(gravity_raw, (int, float)) else None
    if not isinstance(temp_k, (int, float)):
        temp_k = None

    results:list[tuple[str, float]] = []
    for genus, conditions in GENUS_CONDITIONS.items():
        score:float|None = _score_genus(conditions, nearest_star_type, planet_class, atmosphere_type, has_volcanism, temp_k, gravity_g)
        if score is not None:
            results.append((genus, score))

    results.sort(key=lambda pair: pair[1], reverse=True)
    return results
