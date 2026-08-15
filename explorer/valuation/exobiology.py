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

def exceeds_threshold(value_max:int|None, threshold:int) -> bool:
    """ Worth-flagging check -- uses the top of the known range (optimistic), a "worth
    investigating" signal, not a value guarantee. """
    if value_max is None:
        return False
    return value_max >= threshold

def with_first_logged_bonus(value:int, was_footfalled:bool) -> int:
    """ Multiplies by the first-logged bonus (5x total) if WasFootfalled says nobody has set
    foot on this body yet -- see exobiology_data.FIRST_LOGGED_BONUS_MULTIPLIER. """
    return value if was_footfalled else value * exobiology_data.FIRST_LOGGED_BONUS_MULTIPLIER
