"""
Soft ranking bias from a body's known biological_signal_count (the `Count` FSSBodySignals gives
for the "$SAA_SignalType_Biological;" type -- the exact number of distinct genus-level signals
present, one-for-one with what SAASignalsFound will later confirm), layered on top of -- never
replacing -- the physics-based Scan-condition confidence from genus_prediction.py.

Community-reported pattern (only partially independently corroborated -- the low end, "1 signal
is usually Bacterium, occasionally Stratum on a hot body," checks out against public discussion;
the full tiered chain below did not have a citable independent source at the time this was
written). Treated accordingly as a low-confidence TIEBREAK among candidates that already passed
their own real spawn-condition gates in genus_prediction.py -- this module never grants
eligibility a genus/species didn't already earn, only reorders/selects among what's eligible.

Cumulative structure: signal count N's "expected" genus set is the union of every tier <= N,
since each additional signal is reported to ADD a new usual genus on top of the lower tiers
rather than replace them. At signal count 6+ the pattern is reported to "break open" -- no bias
applied there, every condition-eligible candidate is equally plausible (this is also what
happens for any count outside 1-5, or when SIGNAL_COUNT_TIER_GENERA has no bias to offer).

Exception, per direct field report: bodies with a Thin Water, Thin Oxygen, or Thin Nitrogen
atmosphere don't follow this pattern at all -- CHAIN_EXCEPTION_ATMOSPHERES disables the whole
bias for those bodies (falls back to pure Scan-condition confidence ordering).
"""

# Cumulative: signal count N's expected-genus set is the union of tiers 1..N. Excludes the
# tier-1 slot itself, which depends on planet_class (see expected_genera_for_signal_count).
SIGNAL_COUNT_TIER_GENERA:dict[int, list[str]] = {
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

# A lone (signal count 1) body is usually Bacterium; the reported exception is a hot High Metal
# Content body, where the single signal is more often the specific high-value Stratum Tectonicas.
# "Hot enough" isn't a separate threshold here -- Stratum Tectonicas's own (much wider/hotter)
# temperature range in species_conditions.py already gates that; this just says which genus to
# prefer for the lone slot on an HMC body when Stratum Tectonicas is independently eligible.
TIER_1_DEFAULT_GENUS:str = "Bacterium"
TIER_1_HMC_GENUS:str = "Stratum"
TIER_1_HMC_SPECIES:str = "Stratum Tectonicas"

CHAIN_EXCEPTION_ATMOSPHERES:set[str] = {"Water", "Oxygen", "Nitrogen"}
MAX_CHAIN_SIGNAL_COUNT:int = 5 # 6+ signals "breaks open" -- no bias applied above this

def expected_genera_for_signal_count(
    signal_count:int, atmosphere_type:str, planet_class:str, hmc_species_candidate_present:bool,
) -> set[str]|None:
    """
    The cumulative "usually present" genus set for a known biological_signal_count, or None if
    the chain heuristic doesn't apply at all here (count out of the reported 1-5 range, or an
    exception atmosphere). `hmc_species_candidate_present` should be True only when
    TIER_1_HMC_SPECIES is itself already an eligible stored candidate for this body -- see
    genus_prediction.py's hard/soft gating, which this module never bypasses.
    """
    if atmosphere_type in CHAIN_EXCEPTION_ATMOSPHERES:
        return None
    if signal_count < 1 or signal_count > MAX_CHAIN_SIGNAL_COUNT:
        return None

    is_hmc:bool = "High metal content" in (planet_class or "")
    tier_1_genus:str = TIER_1_HMC_GENUS if (is_hmc and hmc_species_candidate_present) else TIER_1_DEFAULT_GENUS

    expected:set[str] = {tier_1_genus}
    for tier in range(2, signal_count + 1):
        expected.update(SIGNAL_COUNT_TIER_GENERA.get(tier, []))
    return expected

def preferred_species_for_tier(genus:str, signal_count:int|None) -> list[str]:
    """ The specific species (if any) this genus's chain entry favors at this signal count. """
    if signal_count is None:
        return []
    return SIGNAL_COUNT_TIER_SPECIES.get(signal_count, {}).get(genus, [])
