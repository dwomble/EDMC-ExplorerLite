"""
Best-effort cartography (scan/mapping) value estimate.

IMPORTANT: this is deliberately approximate. Community-documented formula constants for
Elite Dangerous's exploration payouts are contested across sources (see the implementation
plan's research notes) and may have shifted across game-balance patches. This module's ONLY
job is producing a number good enough to compare against the user's "worth flagging" credit
threshold -- it is never used for the "actual" accumulated totals, which come straight from
`SellExplorationData`/`MultiSellExplorationData` journal events (ground truth, no formula
involved). Keep the constants isolated here so they're easy to recalibrate later without
touching anything else.
"""

MASS_EXPONENT:float = 0.2

# Base credit value per body/star type, before mass scaling. Approximate.
STAR_BASE_K:dict[str, int] = {
    "white_dwarf": 33737,
    "neutron_or_black_hole": 54309,
    "default": 2880,
}

PLANET_BASE_K:dict[str, int] = {
    "metal_rich": 52292,
    "water_or_earthlike": 155581,
    "ammonia": 232619,
    "default": 720,
}

TERRAFORMABLE_BONUS_MULTIPLIER:float = 1.8 # applied on top of the base k for a Terraformable body
FIRST_MAPPED_MULTIPLIER:float = 3.7 # scan value -> full first-discovered+first-mapped+efficient mapping value
EFFICIENT_MAPPING_BONUS:float = 1.25

def _star_category(star_type:str) -> str:
    star_type = (star_type or "").upper()
    if star_type.startswith("D"):
        return "white_dwarf"
    if star_type in ("N", "H", "SUPERMASSIVEBLACKHOLE"):
        return "neutron_or_black_hole"
    return "default"

def _planet_category(planet_class:str) -> str:
    planet_class = (planet_class or "").lower()
    if "metal rich" in planet_class:
        return "metal_rich"
    if "earthlike" in planet_class or "water world" in planet_class:
        return "water_or_earthlike"
    if "ammonia" in planet_class:
        return "ammonia"
    return "default"

def _base_value(k:float, mass:float) -> int:
    mass = max(mass, 0.0001)
    return round(k * (1 + mass ** MASS_EXPONENT))

def estimate_scan_value(scan_entry:dict) -> int:
    """
    Estimate a body's base scan (auto-detect) value, excluding any first-discovery bonus.
    `scan_entry` is a `Scan` journal event dict.
    """
    if "StarType" in scan_entry:
        k:int = STAR_BASE_K[_star_category(scan_entry.get("StarType", ""))]
        mass:float = scan_entry.get("StellarMass", 1.0)
    else:
        k:int = PLANET_BASE_K[_planet_category(scan_entry.get("PlanetClass", ""))]
        mass:float = scan_entry.get("MassEM", 1.0)
        if scan_entry.get("TerraformState") == "Terraformable":
            k = round(k * TERRAFORMABLE_BONUS_MULTIPLIER)

    return _base_value(k, mass)

def estimate_mapping_value(scan_entry:dict, mapped_efficiently:bool = True) -> int:
    """
    Estimate the ceiling mapping value for a body -- assuming first-mapped-by-us and (unless
    told otherwise) an efficient mapping -- excluding any first-discovery bonus. Used pre-DSS
    to decide "is this worth mapping"; refine with the real value once SAAScanComplete confirms
    actual efficiency.
    """
    if "StarType" in scan_entry:
        return 0 # stars aren't DSS-mappable

    return mapping_value_from_scan_value(estimate_scan_value(scan_entry), mapped_efficiently)

def mapping_value_from_scan_value(scan_value:int, mapped_efficiently:bool = True) -> int:
    """ Same scaling as estimate_mapping_value(), starting from an already-known scan value. """
    value:int = round(scan_value * FIRST_MAPPED_MULTIPLIER)
    if mapped_efficiently:
        value = round(value * EFFICIENT_MAPPING_BONUS)
    return value
