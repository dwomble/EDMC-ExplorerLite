"""
Spawn conditions per genus, used by genus_prediction.py to estimate which genera could
plausibly be present on a body BEFORE a DSS/SAASignalsFound reveals the real answer -- keyed
by the same Genus_Localised display names as exobiology_data.py (e.g. "Bacterium", "Tussock"),
so a prediction row can be looked up against that module's value tables directly.

Sourced from real observed-sample statistics -- Canonn's per-genus tracking spreadsheets
(thousands to tens of thousands of confirmed sightings per genus: body type, atmosphere,
volcanism, gravity, temperature, nearby star), supplied directly by the user -- not from
wiki pages or another plugin's rules. Gravity/temperature are the true empirical min/max
across all confirmed samples; body/atmosphere/star-type sets are the union of every value
actually observed; volcanism is treated as required/forbidden only when >=90%/<=10% of
samples agree, otherwise left unconstrained (a genuine mixed signal, not modeled per-species
at this genus-level granularity -- same scope decision as the rest of the plugin).

Only Barnacle (Thargoid, not ordinary planetary exploration) is excluded, matching
exobiology_data.py's existing exclusion of Thargoid biologicals generally -- every other
known genus has real data backing it here.

Field semantics (GenusConditions):
- star_types / planet_classes / atmosphere_types: None = unconstrained (don't check this
  axis, usually because real samples showed too much diversity for it to be a meaningful
  gate); a set = hard gate, body must match one of these to avoid exclusion; atmosphere_types
  as an EMPTY set specifically means "requires no atmosphere" (AtmosphereType == 'None') --
  true for every genus whose tracking data has no atmosphere column at all (Amphora Plant,
  Anemone, Bark Mound, Brain Tree, Crystalline Shard, Sinuous Tuber), a well-established
  real-world fact for these vacuum-adapted organisms, not an inference gap.
- volcanism_required: True/False = hard gate; None = unconstrained/mixed.
- temp_range_k / max_gravity_g: soft -- see genus_prediction.py's tapering, not a hard cutoff
  exactly at the empirical edge, since a finite sample can't rule out a slightly wider true
  range.
"""
from dataclasses import dataclass

@dataclass
class GenusConditions:
    star_types:set[str]|None
    planet_classes:set[str]|None
    atmosphere_types:set[str]|None # empty set = requires AtmosphereType == "None"
    volcanism_required:bool|None
    temp_range_k:tuple[float, float]|None
    max_gravity_g:float|None

GENUS_CONDITIONS:dict[str, GenusConditions] = {
    "Aleoida": GenusConditions(
        star_types=None,
        planet_classes={"Rocky body", "High metal content body"},
        atmosphere_types={"CarbonDioxide"},
        volcanism_required=False,
        temp_range_k=(175.0, 180.0),
        max_gravity_g=0.2696,
    ),
    "Amphora Plant": GenusConditions(
        star_types=None, # real data: meaningful spawns near B/F/G/K/M/L stars too, not just A
        planet_classes={"Metal rich body"},
        atmosphere_types=set(),
        volcanism_required=True,
        temp_range_k=(954.9, 1762.0),
        max_gravity_g=4.47,
    ),
    "Anemone": GenusConditions(
        # Real per-species star lists are consistently exotic across all 8 species (unlike
        # Amphora Plant/Electricae, where ordinary dwarfs show up and the gate isn't real).
        star_types={"A", "AeBe", "B", "F", "H", "K", "N", "O", "W"},
        planet_classes={"High metal content body", "Icy body", "Metal rich body", "Rocky body"},
        atmosphere_types=set(),
        volcanism_required=True,
        temp_range_k=(75.0, 5177.0),
        max_gravity_g=11.01,
    ),
    "Bacterium": GenusConditions(
        star_types=None,
        planet_classes={"High metal content body", "Icy body", "Rocky body", "Rocky ice body", "Water world"},
        atmosphere_types={"Ammonia", "Argon", "ArgonRich", "CarbonDioxide", "Water"},
        volcanism_required=False,
        temp_range_k=(85.8, 1387.9),
        max_gravity_g=1.0008,
    ),
    "Bark Mound": GenusConditions(
        star_types=None,
        planet_classes={"High metal content body", "Icy body", "Metal rich body", "Rocky body", "Rocky ice body"},
        atmosphere_types=set(),
        volcanism_required=True,
        temp_range_k=(184.0, 1712.0),
        max_gravity_g=3.17,
    ),
    "Brain Tree": GenusConditions(
        star_types=None, # real data spans nearly every star type -- not a meaningful gate
        planet_classes={"High metal content body", "Icy body", "Metal rich body", "Rocky body", "Rocky ice body"},
        atmosphere_types=set(),
        volcanism_required=True,
        temp_range_k=(100.0, 1794.0),
        max_gravity_g=4.21,
    ),
    "Cactoida": GenusConditions(
        star_types=None,
        planet_classes={"Rocky body", "High metal content body"},
        atmosphere_types={"Ammonia", "CarbonDioxide"},
        volcanism_required=False,
        temp_range_k=(158.7, 196.7),
        max_gravity_g=0.2721,
    ),
    "Clypeus": GenusConditions(
        star_types=None,
        planet_classes={"Rocky body", "High metal content body"},
        atmosphere_types={"CarbonDioxide", "Water"},
        volcanism_required=False,
        temp_range_k=(190.0, 468.0),
        max_gravity_g=0.2538,
    ),
    "Concha": GenusConditions(
        star_types=None,
        planet_classes={"High metal content body", "Icy body", "Rocky body"},
        atmosphere_types={"Ammonia", "CarbonDioxide", "Methane", "Water"},
        volcanism_required=False,
        temp_range_k=(77.4, 468.0),
        max_gravity_g=0.2691,
    ),
    "Crystalline Shard": GenusConditions(
        star_types={"A", "F", "G", "K", "M", "MS", "S"},
        planet_classes={"High metal content body", "Icy body", "Rocky body", "Rocky ice body"},
        atmosphere_types=set(),
        volcanism_required=True, # real data: 100% of filtered samples had volcanism present
        temp_range_k=(27.0, 250.0),
        max_gravity_g=1.41,
    ),
    "Electricae": GenusConditions(
        star_types=None, # real data includes ordinary M dwarfs alongside exotic remnants -- not a clean gate
        planet_classes={"Icy body"},
        atmosphere_types={"Argon", "ArgonRich", "Neon", "NeonRich"},
        volcanism_required=False,
        temp_range_k=(20.0, 149.7),
        max_gravity_g=0.2752,
    ),
    "Fonticulua": GenusConditions(
        star_types=None,
        planet_classes={"Icy body"},
        atmosphere_types={"Neon", "NeonRich"},
        volcanism_required=False,
        temp_range_k=(50.2, 74.7),
        max_gravity_g=0.2753,
    ),
    "Frutexa": GenusConditions(
        star_types=None,
        planet_classes={"Icy body", "Rocky body"},
        atmosphere_types={"Ammonia", "CarbonDioxide"},
        volcanism_required=False,
        temp_range_k=(114.4, 312.5),
        max_gravity_g=0.2751,
    ),
    "Fumerola": GenusConditions(
        star_types=None,
        planet_classes={"Icy body", "Rocky ice body"},
        atmosphere_types={
            "Ammonia", "Argon", "ArgonRich", "CarbonDioxideRich", "Methane",
            "Neon", "Nitrogen", "Oxygen", "SulphurDioxide",
        },
        volcanism_required=True, # real data: 98% of samples had volcanism present
        temp_range_k=(20.0, 271.3),
        max_gravity_g=0.2741,
    ),
    "Fungoida": GenusConditions(
        star_types=None,
        planet_classes={"High metal content body", "Icy body", "Rocky body", "Rocky ice body"},
        atmosphere_types={"Ammonia", "CarbonDioxide", "Methane"},
        volcanism_required=False,
        temp_range_k=(67.4, 224.7),
        max_gravity_g=0.2751,
    ),
    "Osseus": GenusConditions(
        star_types=None,
        planet_classes={"High metal content body", "Rocky body"},
        atmosphere_types={"Ammonia", "CarbonDioxide"},
        volcanism_required=False,
        temp_range_k=(158.7, 190.0),
        max_gravity_g=0.2714,
    ),
    "Recepta": GenusConditions(
        star_types=None,
        planet_classes={"High metal content body", "Icy body", "Rocky body", "Rocky ice body"},
        atmosphere_types={"Ammonia", "CarbonDioxide", "CarbonDioxideRich", "Oxygen", "SulphurDioxide"},
        volcanism_required=False,
        temp_range_k=(132.0, 272.8),
        max_gravity_g=0.2752,
    ),
    "Sinuous Tuber": GenusConditions(
        star_types=None,
        planet_classes={"High metal content body", "Rocky body", "Rocky ice body"},
        atmosphere_types=set(),
        volcanism_required=None, # no volcanism data tracked for this genus
        temp_range_k=(200.0, 499.0),
        max_gravity_g=3.47,
    ),
    "Stratum": GenusConditions(
        star_types=None,
        planet_classes={"Icy body", "Rocky body"},
        atmosphere_types={"ArgonRich", "CarbonDioxide", "Oxygen", "SulphurDioxide"},
        volcanism_required=False,
        temp_range_k=(85.8, 190.0),
        max_gravity_g=0.5133,
    ),
    "Tubus": GenusConditions(
        star_types=None,
        planet_classes={"Rocky body"},
        atmosphere_types={"CarbonDioxide"},
        volcanism_required=False,
        temp_range_k=(160.0, 195.2),
        max_gravity_g=0.1521,
    ),
    "Tussock": GenusConditions(
        star_types=None,
        planet_classes={"High metal content body", "Rocky body"},
        atmosphere_types={"CarbonDioxide"},
        volcanism_required=False,
        temp_range_k=(145.6, 154.0),
        max_gravity_g=0.1750,
    ),
}
