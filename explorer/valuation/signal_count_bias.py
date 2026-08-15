"""
Soft ranking bias from biological_signal_count (FSSBodySignals' exact count of distinct genus
signals), layered on top of -- never replacing -- genus_prediction.py's real confidence scoring.

Community-reported pattern, only partially corroborated (see conversation history). A tiebreak
among already-eligible candidates only -- never grants eligibility on its own. Cumulative by
tier (1..MAX_CHAIN_SIGNAL_COUNT); tiers 1..MAX_CHAIN_SIGNAL_COUNT stay expected even when the
body's real signal count runs higher -- extra signals beyond that are just unclassified, not
evidence the earlier tiers stopped applying. No bias at all on Thin Water/Oxygen/Nitrogen bodies.

A tier-1 "hot HMC -> Stratum Tectonicas" override used to live here; removed after real journal
data showed it wrongly beating a confirmed Bacterium (Stratum Tectonicas's own range is wide
enough to be "eligible" on almost any warm HMC body).
"""

# Cumulative: signal count N's expected-genus set is the union of tiers 1..N.
SIGNAL_COUNT_TIER_GENERA:dict[int, list[str]] = {
    1: ["Bacterium"],
    2: ["Stratum"],
    3: ["Tussock"],
    4: ["Osseus", "Tubus"], # "usually Osseus ... or occasionally Tubus"
    5: ["Concha", "Frutexa"],
}

# Species-level bias within a genus, keyed by the signal-count tier it's introduced at.
SIGNAL_COUNT_TIER_SPECIES:dict[int, dict[str, list[str]]] = {
    2: {"Stratum": ["Stratum Paleas", "Stratum Laminamus"]},
    3: {"Tussock": ["Tussock Pennatis", "Tussock Capillum"]},
    4: {"Osseus": ["Osseus Spiralis", "Osseus Discus"]},
}

CHAIN_EXCEPTION_ATMOSPHERES:set[str] = {"Water", "Oxygen", "Nitrogen"}
MAX_CHAIN_SIGNAL_COUNT:int = 5 # highest tier we have community data for -- not a cutoff where bias stops

def expected_genera_for_signal_count(signal_count:int, atmosphere_type:str) -> set[str]|None:
    """
    The cumulative "usually present" genus set for a known biological_signal_count, or None if
    the chain heuristic doesn't apply at all here (no signal count yet, or an exception
    atmosphere). A count above MAX_CHAIN_SIGNAL_COUNT still expects all of tiers 1..5 -- the
    extra signals are just unclassified, not proof the known tiers no longer apply.
    """
    if atmosphere_type in CHAIN_EXCEPTION_ATMOSPHERES:
        return None
    if signal_count < 1:
        return None

    expected:set[str] = set()
    for tier in range(1, min(signal_count, MAX_CHAIN_SIGNAL_COUNT) + 1):
        expected.update(SIGNAL_COUNT_TIER_GENERA.get(tier, []))
    return expected

def preferred_species_for_tier(genus:str, signal_count:int|None) -> list[str]:
    """ The specific species (if any) this genus's chain entry favors at this signal count. """
    if signal_count is None:
        return []
    return SIGNAL_COUNT_TIER_SPECIES.get(signal_count, {}).get(genus, [])
