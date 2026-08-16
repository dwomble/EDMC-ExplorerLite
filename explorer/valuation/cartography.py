""" Best-effort cartography (scan/mapping) value estimate -- deliberately approximate, only
used for "worth flagging" comparisons; actual totals come from ground-truth sale events. """

MASS_EXPONENT:float = 0.2

# Base credit value per body/star type, before mass scaling. Approximate.
STAR_BASE_K:dict[str, int] = {
    "white_dwarf": 33737,
    "neutron_or_black_hole": 54309,
    "default": 2880,
}

PLANET_BASE_K:dict[str, int] = {
    "metal_rich": 52292,
    "high_metal_content": 23168,
    "water_or_earthlike": 155581,
    "ammonia": 232619,
    "rocky": 300,
    "default": 720,
}

# Terraform bonus is a separate k-based term added to the base value, not a flat multiplier.
# TERRAFORM_BONUS_FRACTION estimates how much of the max bonus a class typically gets (game
# doesn't expose the real 0-100% terraformability via the journal).
TERRAFORM_BONUS_K:dict[str, int] = {
    "high_metal_content": 241607,
    "water_or_earthlike": 279088,
    "rocky": 223971,
}
TERRAFORM_BONUS_FRACTION:dict[str, float] = {
    "high_metal_content": 0.9,
    "water_or_earthlike": 0.75,
    "rocky": 0.9,
}

FIRST_MAPPED_MULTIPLIER:float = 3.7 # scan value -> full first-discovered+first-mapped+efficient mapping value
EFFICIENT_MAPPING_BONUS:float = 1.25

FIRST_DISCOVERED_BONUS_FRACTION:float = 0.6 # +60% scan value if nobody has discovered this body yet
FIRST_MAPPED_BONUS_FRACTION:float = 0.6 # +60% mapping value if nobody has mapped this body yet -- already
# assumed by FIRST_MAPPED_MULTIPLIER above, so eligibility adjustment backs it out rather than adding it

def _star_category(star_type:str) -> str:
    star_type = (star_type or "").upper()
    if star_type.startswith("D"):
        return "white_dwarf"
    if star_type in ("N", "H", "SUPERMASSIVEBLACKHOLE"):
        return "neutron_or_black_hole"
    return "default"

def _planet_category(planet_class:str) -> str:
    planet_class = (planet_class or "").lower()
    if "gas giant" in planet_class or "water giant" in planet_class:
        return "default" # checked first, else collides with "ammonia" below
    if "metal rich" in planet_class:
        return "metal_rich"
    if "high metal content" in planet_class:
        return "high_metal_content"
    if "earthlike" in planet_class or "water world" in planet_class:
        return "water_or_earthlike"
    if "ammonia" in planet_class:
        return "ammonia"
    if "rocky body" in planet_class:
        return "rocky"
    return "default"

def _mass_factor(mass:float) -> float:
    return 1 + max(mass, 0.0001) ** MASS_EXPONENT

def estimate_scan_value(scan_entry:dict) -> int:
    """ Base scan (auto-detect) value from a `Scan` journal event dict, excluding first-discovery bonus. """
    if "StarType" in scan_entry:
        k:int = STAR_BASE_K[_star_category(scan_entry.get("StarType", ""))]
        mass:float = scan_entry.get("StellarMass", 1.0)
        return round(k * _mass_factor(mass))

    category:str = _planet_category(scan_entry.get("PlanetClass", ""))
    mass:float = scan_entry.get("MassEM", 1.0)
    mass_factor:float = _mass_factor(mass)
    value:float = PLANET_BASE_K[category] * mass_factor

    if scan_entry.get("TerraformState") == "Terraformable" and category in TERRAFORM_BONUS_K:
        value += TERRAFORM_BONUS_K[category] * mass_factor * TERRAFORM_BONUS_FRACTION[category]

    return round(value)

def estimate_mapping_value(scan_entry:dict, mapped_efficiently:bool = True) -> int:
    """ Ceiling mapping value assuming first-mapped-by-us, for pre-DSS "worth mapping" decisions. """
    if "StarType" in scan_entry:
        return 0 # stars aren't DSS-mappable

    return mapping_value_from_scan_value(estimate_scan_value(scan_entry), mapped_efficiently)

def mapping_value_from_scan_value(scan_value:int, mapped_efficiently:bool = True) -> int:
    """ Same scaling as estimate_mapping_value(), starting from an already-known scan value. """
    value:int = round(scan_value * FIRST_MAPPED_MULTIPLIER)
    if mapped_efficiently:
        value = round(value * EFFICIENT_MAPPING_BONUS)
    return value

def scan_value_with_bonus(base_value:int, was_discovered:bool) -> int:
    """ estimate_scan_value()'s base number, plus the first-discovered bonus if WasDiscovered says nobody has yet. """
    return base_value if was_discovered else round(base_value * (1 + FIRST_DISCOVERED_BONUS_FRACTION))

def mapping_value_for_eligibility(mapping_value:int, was_mapped:bool) -> int:
    """ estimate_mapping_value()'s number already assumes first-mapped-by-us -- back out that
    assumed bonus when WasMapped says someone already has, rather than adding one. """
    return mapping_value if not was_mapped else round(mapping_value / (1 + FIRST_MAPPED_BONUS_FRACTION))
