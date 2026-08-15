"""
Value-range lookup helpers over exobiology_data, used by journal handlers to decide whether
a body's exobiology potential clears the user's configured threshold.
"""
from explorer.valuation import exobiology_data

def estimate_genus_range(genus:str) -> tuple[int, int]|None:
    """ (min, max) base credit value across the genus's known species, or None if unknown. """
    return exobiology_data.genus_value_range(genus)

def estimate_confirmed_value(genus:str, species:str) -> int|None:
    """ Exact base credit value once the species is confirmed (first ScanOrganic sample). """
    return exobiology_data.species_value(genus, species)

def genus_from_codex_name(name_localised:str) -> str|None:
    """ Match a CodexEntry event's Name_Localised (e.g. "Tussock Propagito - Lime") back to its
    genus -- strips the trailing " - <color>" variant suffix, if any, then looks up the
    resulting species name. """
    species_name:str = name_localised.split(" - ")[0].strip()
    return exobiology_data.genus_from_species_name(species_name)

def exceeds_threshold(value_max:int|None, threshold:int) -> bool:
    """
    Whether a body's exobiology potential is worth flagging. Uses the top of the known
    range (optimistic) since this is a "worth investigating" signal at a stage where the
    exact species isn't known yet, not a value guarantee.
    """
    if value_max is None:
        return False
    return value_max >= threshold
