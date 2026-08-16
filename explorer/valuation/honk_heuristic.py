""" Honk verdict heuristic, tiered by star type. """

ALWAYS_WORTH_IT_TYPES:set[str] = {"F", "G", "K", "N", "H", "SUPERMASSIVEBLACKHOLE"}
DWARF_TYPES:set[str] = {"M", "L", "T", "Y"}

DWARF_BODY_COUNT:int = 6
OTHER_BODY_COUNT:int = 3

def _star_tier(star_type:str) -> str:
    star_type = (star_type or "").upper()
    if star_type in ALWAYS_WORTH_IT_TYPES:
        return "always"
    if star_type in DWARF_TYPES:
        return "dwarf"
    return "other"

def _best_tier(star_types:list[str]) -> str:
    tiers:set[str] = {_star_tier(t) for t in star_types} or {"other"}
    if "always" in tiers:
        return "always"
    if "other" in tiers:
        return "other"
    return "dwarf"

def assess(body_count:int, star_types:list[str]) -> str:
    """ Return a short (panel-friendly) verdict string. """
    if body_count == 0:
        return "no bodies"

    tier:str = _best_tier(star_types)
    if tier == "always":
        return "worth a full scan" if body_count > 1 else "probably quiet" # >1 is our proxy for "has any planets"
    threshold:int = DWARF_BODY_COUNT if tier == "dwarf" else OTHER_BODY_COUNT
    return "worth a full scan" if body_count >= threshold else "probably quiet"
