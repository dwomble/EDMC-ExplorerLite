"""
Spawn conditions per genus, used by genus_prediction.py to estimate which genera could
plausibly be present on a body BEFORE a DSS/SAASignalsFound reveals the real answer -- keyed
by the same Genus_Localised display names as exobiology_data.py (e.g. "Bacterium", "Tussock").

A genus is modeled as a list of independent RULESETS (OR'd) -- matches earlier attempt's
mistake of modeling one condition-blob per genus, which silently dropped real spawn niches
(e.g. Bacterium is genuinely absent from Sulphur Dioxide atmospheres in one species' data but
present via two OTHERS -- a single genus-wide blob can't represent that, a real body is
eligible for a genus if it satisfies ANY ONE of that genus's rulesets, same as the real game's
per-species-per-atmosphere condition structure). Within a single ruleset, every field present
is AND'd; a field left None is unconstrained for that ruleset.

Sourced by reading Silarn/EDMC-BioScan (github.com/Silarn/EDMC-BioScan, GPLv2) locally as a
reference and independently transcribing/restructuring the numeric spawn parameters into our
own dataclass shape and code -- not copying its files, data structures, or prose. This project
stays permissively (MIT) licensed; BioScan is read-only reference material for verifying
facts, same policy as exobiology_data.py's own sourcing. Per-species distinctions are
deliberately flattened to genus level (all of a genus's species' rulesets pooled together) --
this plugin predicts GENUS only, matching its existing scope decision not to guess species.

Several rulesets carry a "# unmodeled: ..." comment -- these note real spawn conditions that
don't fit the fields available from a Scan event (system-wide co-occurrence checks ("bodies"),
galactic region/nebula/Guardian-ruin proximity ("regions"/"nebula"/"guardian"/"tuber"), a
specific home system ("system"), atmosphere gas percentage floors ("atmosphere_component"),
orbital period, or distance-from-arrival bounds). Those specific conditions are simply not
checked -- the ruleset still applies based on whatever fields it DOES have, so predictions for
genera whose only rulesets carry these (Bark Mound, Amphora Plant, Crystalline Shard, some
Anemone/Brain Tree/Sinuous Tuber rulesets) will over-fire outside their real niche. Accepted,
not solved -- flagged per-ruleset so it's visible exactly where the gap is.

Field semantics (Ruleset):
- atmosphere / body_types / star_types: None = unconstrained; a set = hard gate, the body's
  actual value must be a member (atmosphere includes the literal "None" as a settable member
  for airless-required rulesets, matching the real AtmosphereType string for airless bodies).
- min/max_gravity_g, min/max_temp_k, min/max_pressure_atm: soft bounds -- see
  genus_prediction.py's tapering, not a hard cutoff exactly at the edge.
- volcanism: None = unconstrained; 'any' = must have some volcanism; 'none' = must have none;
  a set of strings = the real Volcanism string must contain one of these as a substring
  (mirrors BioScan's own matching, which is itself just checking against the raw journal text).
"""
from dataclasses import dataclass

@dataclass
class Ruleset:
    atmosphere:set[str]|None
    body_types:set[str]|None
    star_types:set[str]|None
    min_gravity_g:float|None
    max_gravity_g:float|None
    min_temp_k:float|None
    max_temp_k:float|None
    min_pressure_atm:float|None
    max_pressure_atm:float|None
    volcanism:str|set[str]|None # None, 'any', 'none', or a set of substring keywords

GENUS_RULESETS:dict[str, list[Ruleset]] = {
    "Aleoida": [
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=175.0, max_temp_k=180.0, min_pressure_atm=0.0161, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=190.0, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=170.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=190.0, max_temp_k=197.0, min_pressure_atm=0.054, max_pressure_atm=None, volcanism='none'),
    ],
    "Amphora Plant": [
        Ruleset(atmosphere={'None'}, body_types={'Metal rich body'}, star_types={'A'}, min_gravity_g=None, max_gravity_g=None, min_temp_k=1000.0, max_temp_k=1750.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate'}),  # unmodeled: bodies, regions
    ],
    "Anemone": [
        Ruleset(atmosphere=None, body_types={'Rocky body'}, star_types={'B'}, min_gravity_g=0.044, max_gravity_g=1.28, min_temp_k=200.0, max_temp_k=440.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate', 'water'}),  # unmodeled: regions
        Ruleset(atmosphere=None, body_types={'Rocky body'}, star_types={'A', 'B'}, min_gravity_g=0.047, max_gravity_g=0.37, min_temp_k=200.0, max_temp_k=440.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate'}),  # unmodeled: regions
        Ruleset(atmosphere=None, body_types={'Icy body', 'Rocky ice body'}, star_types={'O'}, min_gravity_g=0.17, max_gravity_g=2.52, min_temp_k=65.0, max_temp_k=800.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere=None, body_types={'Icy body', 'Rocky ice body'}, star_types={'O'}, min_gravity_g=0.17, max_gravity_g=2.52, min_temp_k=65.0, max_temp_k=800.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon dioxide geysers'}),  # unmodeled: regions
        Ruleset(atmosphere=None, body_types={'Rocky body'}, star_types={'B'}, min_gravity_g=0.045, max_gravity_g=0.37, min_temp_k=200.0, max_temp_k=440.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate'}),  # unmodeled: regions
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body'}, star_types={'A', 'B', 'N'}, min_gravity_g=0.036, max_gravity_g=4.61, min_temp_k=160.0, max_temp_k=1800.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body', 'Rocky body'}, star_types={'O'}, min_gravity_g=0.036, max_gravity_g=None, min_temp_k=110.0, max_temp_k=3050.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body'}, star_types={'B'}, min_gravity_g=0.036, max_gravity_g=4.61, min_temp_k=400.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body'}, star_types={'B'}, min_gravity_g=None, max_gravity_g=None, min_temp_k=220.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),  # unmodeled: regions
    ],
    "Bacterium": [
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.039, max_gravity_g=0.608, min_temp_k=145.0, max_temp_k=400.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Helium'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.55, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.067, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Helium'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.7, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.067, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Argon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.15, max_gravity_g=0.26, min_temp_k=56, max_temp_k=150, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon dioxide', 'methane'}),
        Ruleset(atmosphere={'Helium'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.48, max_gravity_g=0.51, min_temp_k=20, max_temp_k=21, min_pressure_atm=0.075, max_pressure_atm=None, volcanism={'methane'}),
        Ruleset(atmosphere={'Methane'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.047, min_temp_k=84, max_temp_k=110, min_pressure_atm=0.03, max_pressure_atm=None, volcanism={'methane'}),
        Ruleset(atmosphere={'Neon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.61, min_temp_k=20, max_temp_k=65, min_pressure_atm=None, max_pressure_atm=0.008, volcanism={'carbon dioxide', 'methane'}),
        Ruleset(atmosphere={'NeonRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.61, min_temp_k=20, max_temp_k=65, min_pressure_atm=0.005, max_pressure_atm=None, volcanism={'carbon dioxide', 'methane'}),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.2, max_gravity_g=0.3, min_temp_k=60, max_temp_k=70, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon dioxide', 'methane'}),
        Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.4, min_temp_k=150, max_temp_k=220, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'carbon dioxide', 'methane'}),
        Ruleset(atmosphere={'Neon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.255, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=61.0, min_pressure_atm=None, max_pressure_atm=0.01, volcanism=None),
        Ruleset(atmosphere={'Argon'}, body_types=None, star_types=None, min_gravity_g=0.027, max_gravity_g=0.51, min_temp_k=50.0, max_temp_k=245.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.376, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        Ruleset(atmosphere={'Argon'}, body_types={'High metal content body', 'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.45, min_temp_k=50.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'ArgonRich'}, body_types=None, star_types=None, min_gravity_g=0.24, max_gravity_g=0.45, min_temp_k=50.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=0.05, volcanism='any'),
        Ruleset(atmosphere={'Ammonia'}, body_types=None, star_types=None, min_gravity_g=0.025, max_gravity_g=0.23, min_temp_k=165.0, max_temp_k=177.0, min_pressure_atm=0.0025, max_pressure_atm=0.02, volcanism='any'),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types=None, star_types=None, min_gravity_g=0.45, max_gravity_g=0.61, min_temp_k=300.0, max_temp_k=None, min_pressure_atm=0.006, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'CarbonDioxide', 'CarbonDioxideRich'}, body_types=None, star_types=None, min_gravity_g=0.025, max_gravity_g=0.61, min_temp_k=167.0, max_temp_k=None, min_pressure_atm=0.006, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'Helium'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.067, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'Methane'}, body_types={'High metal content body', 'Icy body', 'Rocky body'}, star_types=None, min_gravity_g=0.026, max_gravity_g=0.126, min_temp_k=80.0, max_temp_k=109.0, min_pressure_atm=0.012, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'Neon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=95.0, min_pressure_atm=None, max_pressure_atm=0.008, volcanism='any'),
        Ruleset(atmosphere={'NeonRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=95.0, min_pressure_atm=0.003, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'Nitrogen'}, body_types=None, star_types=None, min_gravity_g=0.21, max_gravity_g=0.35, min_temp_k=55.0, max_temp_k=80.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'Oxygen'}, body_types=None, star_types=None, min_gravity_g=0.23, max_gravity_g=0.5, min_temp_k=150.0, max_temp_k=240.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types=None, star_types=None, min_gravity_g=0.18, max_gravity_g=0.61, min_temp_k=148.0, max_temp_k=550.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types=None, star_types=None, min_gravity_g=0.18, max_gravity_g=0.61, min_temp_k=300.0, max_temp_k=550.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.5, max_gravity_g=0.55, min_temp_k=500.0, max_temp_k=650.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.063, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'WaterRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.315, max_gravity_g=0.44, min_temp_k=190.0, max_temp_k=330.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.05, max_gravity_g=0.6, min_temp_k=42.5, max_temp_k=151.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.17, max_gravity_g=0.63, min_temp_k=50.0, max_temp_k=90.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Oxygen'}, body_types=None, star_types=None, min_gravity_g=0.239, max_gravity_g=0.61, min_temp_k=143.5, max_temp_k=246.0, min_pressure_atm=0.013, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Methane'}, body_types=None, star_types=None, min_gravity_g=0.0245, max_gravity_g=0.35, min_temp_k=67.0, max_temp_k=109.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'MethaneRich'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.44, max_gravity_g=0.6, min_temp_k=74.0, max_temp_k=141.0, min_pressure_atm=0.01, max_pressure_atm=0.05, volcanism='none'),
        Ruleset(atmosphere={'Argon'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.45, min_temp_k=50.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'ArgonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.45, min_temp_k=80.0, max_temp_k=90.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'Helium'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.51, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.065, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'Methane'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.0265, max_gravity_g=0.0455, min_temp_k=84.0, max_temp_k=108.0, min_pressure_atm=0.035, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'Neon'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.31, max_gravity_g=0.6, min_temp_k=20.0, max_temp_k=61.0, min_pressure_atm=None, max_pressure_atm=0.0065, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'NeonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=93.0, min_pressure_atm=0.0027, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.2, max_gravity_g=0.26, min_temp_k=60.0, max_temp_k=80.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'WaterRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.38, max_gravity_g=0.45, min_temp_k=190.0, max_temp_k=330.0, min_pressure_atm=0.07, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.605, min_temp_k=132.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.064, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.064, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'WaterRich'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.5, min_temp_k=190.0, max_temp_k=330.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Ammonia'}, body_types={'Icy body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.03, max_gravity_g=0.09, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism={'water'}),
        Ruleset(atmosphere={'Argon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.165, max_gravity_g=0.33, min_temp_k=57.5, max_temp_k=145.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'ArgonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.08, min_temp_k=80.0, max_temp_k=90.0, min_pressure_atm=None, max_pressure_atm=0.01, volcanism={'water'}),
        Ruleset(atmosphere={'CarbonDioxide', 'CarbonDioxideRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.25, max_gravity_g=0.32, min_temp_k=167.0, max_temp_k=240.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Helium'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.49, max_gravity_g=0.53, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.065, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Neon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.29, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=51.0, min_pressure_atm=None, max_pressure_atm=0.075, volcanism={'water'}),
        Ruleset(atmosphere={'NeonRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.43, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=65.0, min_pressure_atm=0.005, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.205, max_gravity_g=0.241, min_temp_k=60.0, max_temp_k=80.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.24, max_gravity_g=0.35, min_temp_k=154.0, max_temp_k=220.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.054, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
    ],
    "Bark Mound": [
        Ruleset(atmosphere=None, body_types=None, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),  # unmodeled: nebula, regions
    ],
    "Brain Tree": [
        Ruleset(atmosphere=None, body_types=None, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),  # unmodeled: guardian, region
        Ruleset(atmosphere=None, body_types={'Rocky body'}, star_types=None, min_gravity_g=None, max_gravity_g=0.42, min_temp_k=200.0, max_temp_k=400.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate', 'water'}),  # unmodeled: bodies, guardian, region
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body', 'Rocky body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate'}),  # unmodeled: guardian, region
        Ruleset(atmosphere=None, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=None, max_gravity_g=0.4, min_temp_k=100.0, max_temp_k=270.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),  # unmodeled: bodies, guardian, region
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body'}, star_types=None, min_gravity_g=None, max_gravity_g=2.9, min_temp_k=300.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate'}),  # unmodeled: guardian, region
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),  # unmodeled: bodies, guardian, region
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=None, max_gravity_g=2.7, min_temp_k=300.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate'}),  # unmodeled: bodies, guardian, region
        Ruleset(atmosphere=None, body_types={'Rocky body'}, star_types=None, min_gravity_g=None, max_gravity_g=0.5, min_temp_k=300.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate', 'water'}),  # unmodeled: guardian, region
    ],
    "Cactoida": [
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=197.0, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.265, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=210.0, min_pressure_atm=None, max_pressure_atm=0.005, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=197.0, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
    ],
    "Clypeus": [
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=190.0, max_temp_k=None, min_pressure_atm=0.054, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=190.0, max_temp_k=197.0, min_pressure_atm=0.054, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=190.0, max_temp_k=197.0, min_pressure_atm=0.055, max_pressure_atm=None, volcanism='none'),  # unmodeled: distance
        Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: distance
        Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),  # unmodeled: distance
    ],
    "Concha": [
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.045, min_temp_k=176.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'silicate'}),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=None, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Methane'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.15, min_temp_k=78.0, max_temp_k=100.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'metallic', 'silicate'}),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.65, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.65, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=200.0, min_pressure_atm=0.002, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.053, max_gravity_g=0.275, min_temp_k=42.0, max_temp_k=52.0, min_pressure_atm=None, max_pressure_atm=0.0047, volcanism='none'),
    ],
    "Crystalline Shard": [
        Ruleset(atmosphere={'Argon', 'ArgonRich', 'CarbonDioxide', 'CarbonDioxideRich', 'Helium', 'Methane', 'Neon', 'NeonRich', 'None'}, body_types=None, star_types={'A', 'F', 'G', 'K', 'MS', 'S'}, min_gravity_g=None, max_gravity_g=2.0, min_temp_k=None, max_temp_k=273.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: bodies, distance, regions
    ],
    "Electricae": [
        Ruleset(atmosphere={'Argon', 'ArgonRich'}, body_types={'Icy body'}, star_types={'A', 'AeBe', 'D', 'H', 'N'}, min_gravity_g=0.025, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Neon', 'NeonRich'}, body_types={'Icy body'}, star_types={'A', 'AeBe', 'D', 'H', 'N'}, min_gravity_g=0.26, max_gravity_g=0.276, min_temp_k=20.0, max_temp_k=70.0, min_pressure_atm=None, max_pressure_atm=0.005, volcanism=None),
        Ruleset(atmosphere={'Argon', 'ArgonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: nebula
        Ruleset(atmosphere={'Neon', 'NeonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.026, max_gravity_g=0.276, min_temp_k=20.0, max_temp_k=70.0, min_pressure_atm=None, max_pressure_atm=0.005, volcanism=None),  # unmodeled: nebula
    ],
    "Fonticulua": [
        Ruleset(atmosphere={'Neon', 'NeonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.25, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=75.0, min_pressure_atm=None, max_pressure_atm=0.006, volcanism='none'),
        Ruleset(atmosphere={'Argon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.027, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'ArgonRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.209, max_gravity_g=0.276, min_temp_k=61.0, max_temp_k=125.0, min_pressure_atm=0.0175, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.19, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=81.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.235, max_gravity_g=0.276, min_temp_k=143.0, max_temp_k=200.0, min_pressure_atm=0.012, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Methane'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.07, min_temp_k=83.0, max_temp_k=109.0, min_pressure_atm=0.03, max_pressure_atm=None, volcanism=None),
    ],
    "Frutexa": [
        Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.237, min_temp_k=146.0, max_temp_k=197.0, min_pressure_atm=0.0029, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=176.0, min_pressure_atm=None, max_pressure_atm=0.01, volcanism='none'),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=146.0, max_temp_k=197.0, min_pressure_atm=0.002, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Methane'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.05, max_gravity_g=0.1, min_temp_k=100.0, max_temp_k=300.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.07, min_temp_k=None, max_temp_k=400.0, min_pressure_atm=None, max_pressure_atm=0.07, volcanism='none'),
        Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=146.0, max_temp_k=197.0, min_pressure_atm=0.003, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.056, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.056, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=215.0, min_pressure_atm=None, max_pressure_atm=0.004, volcanism=None),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.265, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=135.0, min_pressure_atm=None, max_pressure_atm=0.004, volcanism='none'),
    ],
    "Fumerola": [
        Ruleset(atmosphere={'Argon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.168, max_gravity_g=0.276, min_temp_k=57.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon', 'methane'}),
        Ruleset(atmosphere={'Methane'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.047, min_temp_k=84.0, max_temp_k=110.0, min_pressure_atm=0.03, max_pressure_atm=None, volcanism={'methane magma'}),
        Ruleset(atmosphere={'Neon'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.26, max_gravity_g=0.276, min_temp_k=40.0, max_temp_k=60.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon', 'methane'}),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.2, max_gravity_g=0.276, min_temp_k=57.0, max_temp_k=70.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon', 'methane'}),
        Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.26, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon'}),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.185, max_gravity_g=0.276, min_temp_k=149.0, max_temp_k=272.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon', 'methane'}),
        Ruleset(atmosphere={'Ammonia', 'ArgonRich', 'CarbonDioxideRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=None, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon'}),
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.09, min_temp_k=161.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism={'metallic', 'rocky', 'silicate'}),
        Ruleset(atmosphere={'Argon'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.07, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=121.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate'}),
        Ruleset(atmosphere={'Methane'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.127, min_temp_k=77.0, max_temp_k=109.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate'}),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.07, max_gravity_g=0.276, min_temp_k=54.0, max_temp_k=210.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate'}),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.05, max_gravity_g=0.276, min_temp_k=500.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'metallic', 'rocky', 'silicate'}),
        Ruleset(atmosphere={'Neon'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=30.0, max_temp_k=129.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'Argon', 'ArgonRich', 'NeonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.044, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=141.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'Methane'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.1, min_temp_k=83.0, max_temp_k=109.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'nitrogen'}),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.21, max_gravity_g=0.276, min_temp_k=60.0, max_temp_k=81.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=None, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.21, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=250.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'ammonia', 'nitrogen'}),
        Ruleset(atmosphere={'Ammonia'}, body_types={'Icy body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.028, max_gravity_g=0.276, min_temp_k=161.0, max_temp_k=177.0, min_pressure_atm=0.002, max_pressure_atm=0.02, volcanism={'water'}),
        Ruleset(atmosphere={'Argon', 'ArgonRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.166, max_gravity_g=0.276, min_temp_k=57.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.25, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=0.01, max_pressure_atm=0.03, volcanism={'water'}),
        Ruleset(atmosphere={'Methane'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=80.0, max_temp_k=100.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Neon'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.26, max_gravity_g=0.276, min_temp_k=20.0, max_temp_k=60.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.195, max_gravity_g=0.245, min_temp_k=56.0, max_temp_k=80.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.276, min_temp_k=153.0, max_temp_k=190.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Icy body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.18, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=270.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.06, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
    ],
    "Fungoida": [
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        Ruleset(atmosphere={'Methane'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.033, max_gravity_g=0.276, min_temp_k=68.0, max_temp_k=109.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Methane'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.033, max_gravity_g=0.276, min_temp_k=67.0, max_temp_k=109.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.045, min_temp_k=172.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'silicate'}),  # unmodeled: regions
        Ruleset(atmosphere={'Argon'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.2, max_gravity_g=0.23, min_temp_k=60.0, max_temp_k=90.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'rocky', 'silicate'}),  # unmodeled: regions
        Ruleset(atmosphere={'ArgonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.3, max_gravity_g=0.5, min_temp_k=60.0, max_temp_k=90.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.0405, max_gravity_g=0.27, min_temp_k=180.0, max_temp_k=None, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Methane'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.043, max_gravity_g=0.126, min_temp_k=78.5, max_temp_k=109.0, min_pressure_atm=0.012, max_pressure_atm=None, volcanism={'major silicate'}),  # unmodeled: regions
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.039, max_gravity_g=0.064, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Argon'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.058, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=129.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.155, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=70.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Argon'}, body_types={'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.041, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism={'major silicate'}),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.071, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism={'major silicate'}),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.071, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism={'major rocky'}),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.041, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=None, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Methane'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.044, max_gravity_g=0.125, min_temp_k=80.0, max_temp_k=110.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'major metallic', 'major silicate'}),  # unmodeled: regions
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.039, max_gravity_g=0.063, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
    ],
    "Osseus": [
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=None, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.088, min_temp_k=161.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism='any'),
        Ruleset(atmosphere={'Argon'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.2, max_gravity_g=0.276, min_temp_k=65.0, max_temp_k=120.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.026, max_gravity_g=0.276, min_temp_k=500.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'Methane'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.127, min_temp_k=80.0, max_temp_k=110.0, min_pressure_atm=0.012, max_pressure_atm=None, volcanism='any'),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.055, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        Ruleset(atmosphere={'Argon'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.059, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=135.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Argon'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.059, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=135.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'geysers', 'water'}),
        Ruleset(atmosphere={'ArgonRich'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.035, max_gravity_g=0.276, min_temp_k=60.0, max_temp_k=80.5, min_pressure_atm=0.03, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Methane'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.033, max_gravity_g=0.276, min_temp_k=67.0, max_temp_k=109.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Nitrogen'}, body_types={'High metal content body', 'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.05, max_gravity_g=0.276, min_temp_k=42.0, max_temp_k=70.1, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.0405, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=None, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.0405, max_gravity_g=0.276, min_temp_k=191.0, max_temp_k=None, min_pressure_atm=0.057, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
    ],
    "Recepta": [
        Ruleset(atmosphere={'CarbonDioxide'}, body_types=None, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=151.0, max_temp_k=200.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: atmosphere_component
        Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.276, min_temp_k=154.0, max_temp_k=175.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='none'),  # unmodeled: atmosphere_component
        Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.276, min_temp_k=154.0, max_temp_k=175.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'water'}),  # unmodeled: atmosphere_component
        Ruleset(atmosphere={'SulphurDioxide'}, body_types=None, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=273.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: atmosphere_component
        Ruleset(atmosphere={'CarbonDioxide'}, body_types=None, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=195.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: atmosphere_component
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=195.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),  # unmodeled: atmosphere_component
        Ruleset(atmosphere={'SulphurDioxide'}, body_types=None, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=272.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: atmosphere_component
        Ruleset(atmosphere={'CarbonDioxide', 'CarbonDioxideRich'}, body_types={'High metal content body', 'Icy body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=195.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: atmosphere_component
        Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.276, min_temp_k=154.0, max_temp_k=175.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='none'),  # unmodeled: atmosphere_component
        Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.276, min_temp_k=154.0, max_temp_k=175.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'water'}),  # unmodeled: atmosphere_component
        Ruleset(atmosphere={'SulphurDioxide'}, body_types=None, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=275.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: atmosphere_component
    ],
    "Sinuous Tuber": [
        Ruleset(atmosphere=None, body_types={'High metal content body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'rocky magma'}),  # unmodeled: tuber
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body', 'Rocky body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),  # unmodeled: tuber
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'major rocky magma', 'major silicate vapour'}),  # unmodeled: tuber
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'major rocky magma', 'major silicate vapour'}),  # unmodeled: regions
        Ruleset(atmosphere=None, body_types={'Rocky body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'major metallic magma', 'major silicate vapour'}),  # unmodeled: max_orbital_period, tuber
        Ruleset(atmosphere=None, body_types={'Rocky body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'major silicate vapour'}),  # unmodeled: max_orbital_period, tuber
        Ruleset(atmosphere=None, body_types={'Rocky body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'major silicate vapour'}),  # unmodeled: regions
        Ruleset(atmosphere=None, body_types={'Rocky body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'major silicate vapour'}),  # unmodeled: max_orbital_period, tuber
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'major rocky magma', 'major silicate vapour'}),  # unmodeled: tuber
        Ruleset(atmosphere=None, body_types={'High metal content body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'major rocky magma', 'major silicate vapour'}),  # unmodeled: tuber
        Ruleset(atmosphere=None, body_types={'Rocky body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'major rocky magma', 'major silicate vapour'}),  # unmodeled: max_orbital_period, tuber
        Ruleset(atmosphere=None, body_types={'High metal content body', 'Metal rich body'}, star_types=None, min_gravity_g=None, max_gravity_g=None, min_temp_k=200.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'=metallic magma volcanism', '=rocky magma volcanism', 'major silicate vapour'}),  # unmodeled: tuber
    ],
    "Stratum": [
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.48, min_temp_k=165.0, max_temp_k=190.0, min_pressure_atm=0.0035, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.4, min_temp_k=165.0, max_temp_k=190.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.35, min_temp_k=165.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.585, min_temp_k=165.0, max_temp_k=395.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'CarbonDioxideRich'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.43, max_gravity_g=0.585, min_temp_k=185.0, max_temp_k=260.0, min_pressure_atm=0.015, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.056, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.056, min_temp_k=None, max_temp_k=None, min_pressure_atm=0.065, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Oxygen'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.39, max_gravity_g=0.59, min_temp_k=165.0, max_temp_k=250.0, min_pressure_atm=0.022, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.34, min_temp_k=165.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.26, max_gravity_g=0.57, min_temp_k=165.0, max_temp_k=373.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.03, max_gravity_g=0.4, min_temp_k=165.0, max_temp_k=190.0, min_pressure_atm=0.05, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.4, min_temp_k=165.0, max_temp_k=190.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.6, min_temp_k=191.0, max_temp_k=371.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxideRich'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.44, max_gravity_g=0.56, min_temp_k=210.0, max_temp_k=246.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Oxygen'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.6, min_temp_k=200.0, max_temp_k=250.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.26, max_gravity_g=0.55, min_temp_k=191.0, max_temp_k=373.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.38, min_temp_k=165.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Argon', 'ArgonRich'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.485, max_gravity_g=0.54, min_temp_k=167.0, max_temp_k=199.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.61, min_temp_k=165.0, max_temp_k=430.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'CarbonDioxideRich'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.035, max_gravity_g=0.61, min_temp_k=165.0, max_temp_k=260.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Oxygen'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.52, min_temp_k=165.0, max_temp_k=246.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.29, max_gravity_g=0.62, min_temp_k=165.0, max_temp_k=450.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.063, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.043, max_gravity_g=0.54, min_temp_k=191.0, max_temp_k=365.0, min_pressure_atm=0.001, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxideRich'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.45, max_gravity_g=0.56, min_temp_k=200.0, max_temp_k=250.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.29, max_gravity_g=0.52, min_temp_k=191.0, max_temp_k=369.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
    ],
    "Tubus": [
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.041, max_gravity_g=0.153, min_temp_k=160.0, max_temp_k=197.0, min_pressure_atm=0.003, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.152, min_temp_k=160.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.152, min_temp_k=160.0, max_temp_k=195.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.152, min_temp_k=160.0, max_temp_k=197.0, min_pressure_atm=0.003, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.153, min_temp_k=160.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.153, min_temp_k=160.0, max_temp_k=197.0, min_pressure_atm=0.003, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
    ],
    "Tussock": [
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.09, min_temp_k=146.0, max_temp_k=154.0, min_pressure_atm=0.00289, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.13, min_temp_k=155.0, max_temp_k=160.0, min_pressure_atm=0.00289, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.2, min_temp_k=161.0, max_temp_k=170.0, min_pressure_atm=0.00289, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=147.0, max_temp_k=197.0, min_pressure_atm=0.00289, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.23, min_temp_k=171.0, max_temp_k=174.0, min_pressure_atm=0.01, max_pressure_atm=0.071, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.276, min_temp_k=175.0, max_temp_k=180.0, min_pressure_atm=0.016, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=145.0, max_temp_k=197.0, min_pressure_atm=0.00289, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.041, max_gravity_g=0.27, min_temp_k=181.0, max_temp_k=190.0, min_pressure_atm=0.0275, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=191.0, max_temp_k=197.0, min_pressure_atm=0.058, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        Ruleset(atmosphere={'SulphurDioxide'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=0.01, volcanism=None),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.065, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        Ruleset(atmosphere={'Water'}, body_types={'High metal content body', 'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.065, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        Ruleset(atmosphere={'Argon'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.22, max_gravity_g=0.276, min_temp_k=80.0, max_temp_k=129.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        Ruleset(atmosphere={'Methane'}, body_types={'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.033, max_gravity_g=0.276, min_temp_k=80.0, max_temp_k=110.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
    ],
}
