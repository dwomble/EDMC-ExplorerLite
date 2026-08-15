""" Per-species spawn conditions, narrowing genus_conditions.py's genus-level guesses down to a
specific species (e.g. "Tussock Ignis" vs "Tussock Pennata" by temperature band). Scoped to
atmosphere-bearing genera only -- airless genera stay genus-only via GENUS_RULESETS. Reuses
genus_conditions.py's `Ruleset` dataclass and sourcing policy. Species names must match
exobiology_data.py's SPECIES_VALUE keys exactly. """
from explorer.valuation.genus_conditions import Ruleset

SPECIES_RULESETS:dict[str, dict[str, list[Ruleset]]] = {
    "Aleoida": {
        "Aleoida Arcus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=175.0, max_temp_k=180.0, min_pressure_atm=0.0161, max_pressure_atm=None, volcanism='none'),
        ],
        "Aleoida Coronamus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=190.0, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),
        ],
        "Aleoida Spica": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=170.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        ],
        "Aleoida Laminiae": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        ],
        "Aleoida Gravis": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=190.0, max_temp_k=197.0, min_pressure_atm=0.054, max_pressure_atm=None, volcanism='none'),
        ],
    },
    "Bacterium": {
        "Bacterium Aurasus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.039, max_gravity_g=0.608, min_temp_k=145.0, max_temp_k=400.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        ],
        "Bacterium Nebulus": [
            Ruleset(atmosphere={'Helium'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.55, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.067, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'Helium'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.7, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.067, max_pressure_atm=None, volcanism=None),
        ],
        "Bacterium Scopulum": [
            Ruleset(atmosphere={'Argon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.15, max_gravity_g=0.26, min_temp_k=56.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon dioxide', 'methane'}),
            Ruleset(atmosphere={'Helium'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.48, max_gravity_g=0.51, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.075, max_pressure_atm=None, volcanism={'methane'}),
            Ruleset(atmosphere={'Methane'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.047, min_temp_k=84.0, max_temp_k=110.0, min_pressure_atm=0.03, max_pressure_atm=None, volcanism={'methane'}),
            Ruleset(atmosphere={'Neon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=65.0, min_pressure_atm=None, max_pressure_atm=0.008, volcanism={'carbon dioxide', 'methane'}),
            Ruleset(atmosphere={'NeonRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=65.0, min_pressure_atm=0.005, max_pressure_atm=None, volcanism={'carbon dioxide', 'methane'}),
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.2, max_gravity_g=0.3, min_temp_k=60.0, max_temp_k=70.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon dioxide', 'methane'}),
            Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.40, min_temp_k=150.0, max_temp_k=220.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'carbon dioxide', 'methane'}),
        ],
        "Bacterium Acies": [
            Ruleset(atmosphere={'Neon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.255, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=61.0, min_pressure_atm=None, max_pressure_atm=0.01, volcanism=None),
        ],
        "Bacterium Vesicula": [
            Ruleset(atmosphere={'Argon'}, body_types=None, star_types=None, min_gravity_g=0.027, max_gravity_g=0.51, min_temp_k=50.0, max_temp_k=245.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        ],
        "Bacterium Alcyoneum": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.376, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        ],
        "Bacterium Tela": [
            Ruleset(atmosphere={'Argon'}, body_types={'Icy body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.45, min_temp_k=50.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'ArgonRich'}, body_types=None, star_types=None, min_gravity_g=0.24, max_gravity_g=0.45, min_temp_k=50.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=0.05, volcanism='any'),
            Ruleset(atmosphere={'Ammonia'}, body_types=None, star_types=None, min_gravity_g=0.025, max_gravity_g=0.23, min_temp_k=165.0, max_temp_k=177.0, min_pressure_atm=0.0025, max_pressure_atm=0.02, volcanism='any'),
            Ruleset(atmosphere={'CarbonDioxide'}, body_types=None, star_types=None, min_gravity_g=0.45, max_gravity_g=0.61, min_temp_k=300.0, max_temp_k=None, min_pressure_atm=0.006, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'CarbonDioxide', 'CarbonDioxideRich'}, body_types=None, star_types=None, min_gravity_g=0.025, max_gravity_g=0.61, min_temp_k=167.0, max_temp_k=None, min_pressure_atm=0.006, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'Helium'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.067, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'Methane'}, body_types={'Icy body', 'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.026, max_gravity_g=0.126, min_temp_k=80.0, max_temp_k=109.0, min_pressure_atm=0.012, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'Neon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=95.0, min_pressure_atm=None, max_pressure_atm=0.008, volcanism='any'),
            Ruleset(atmosphere={'NeonRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=95.0, min_pressure_atm=0.003, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'Nitrogen'}, body_types=None, star_types=None, min_gravity_g=0.21, max_gravity_g=0.35, min_temp_k=55.0, max_temp_k=80.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'Oxygen'}, body_types=None, star_types=None, min_gravity_g=0.23, max_gravity_g=0.5, min_temp_k=150.0, max_temp_k=240.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'SulphurDioxide'}, body_types=None, star_types=None, min_gravity_g=0.18, max_gravity_g=0.61, min_temp_k=148.0, max_temp_k=550.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'SulphurDioxide'}, body_types=None, star_types=None, min_gravity_g=0.18, max_gravity_g=0.61, min_temp_k=300.0, max_temp_k=550.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.5, max_gravity_g=0.55, min_temp_k=500.0, max_temp_k=650.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.063, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'WaterRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.315, max_gravity_g=0.44, min_temp_k=190.0, max_temp_k=330.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='any'),
        ],
        "Bacterium Informem": [
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.05, max_gravity_g=0.6, min_temp_k=42.5, max_temp_k=151.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.17, max_gravity_g=0.63, min_temp_k=50.0, max_temp_k=90.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        ],
        "Bacterium Volu": [
            Ruleset(atmosphere={'Oxygen'}, body_types=None, star_types=None, min_gravity_g=0.239, max_gravity_g=0.61, min_temp_k=143.5, max_temp_k=246.0, min_pressure_atm=0.013, max_pressure_atm=None, volcanism=None),
        ],
        "Bacterium Bullaris": [
            Ruleset(atmosphere={'Methane'}, body_types=None, star_types=None, min_gravity_g=0.0245, max_gravity_g=0.35, min_temp_k=67.0, max_temp_k=109.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'MethaneRich'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.44, max_gravity_g=0.6, min_temp_k=74.0, max_temp_k=141.0, min_pressure_atm=0.01, max_pressure_atm=0.05, volcanism='none'),
        ],
        "Bacterium Omentum": [
            Ruleset(atmosphere={'Argon'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.45, min_temp_k=50.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'ArgonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.45, min_temp_k=80.0, max_temp_k=90.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'Helium'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.51, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.065, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'Methane'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.0265, max_gravity_g=0.0455, min_temp_k=84.0, max_temp_k=108.0, min_pressure_atm=0.035, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'Neon'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.31, max_gravity_g=0.6, min_temp_k=20.0, max_temp_k=61.0, min_pressure_atm=None, max_pressure_atm=0.0065, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'NeonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=93.0, min_pressure_atm=0.0027, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.2, max_gravity_g=0.26, min_temp_k=60.0, max_temp_k=80.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'WaterRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.38, max_gravity_g=0.45, min_temp_k=190.0, max_temp_k=330.0, min_pressure_atm=0.07, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
        ],
        "Bacterium Cerbrus": [
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.605, min_temp_k=132.0, max_temp_k=500.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.064, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.064, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'WaterRich'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.5, min_temp_k=190.0, max_temp_k=330.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        ],
        "Bacterium Verrata": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'Rocky ice body', 'Icy body'}, star_types=None, min_gravity_g=0.03, max_gravity_g=0.09, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism={'water'}),
            Ruleset(atmosphere={'Argon'}, body_types={'Rocky ice body', 'Icy body'}, star_types=None, min_gravity_g=0.165, max_gravity_g=0.33, min_temp_k=57.5, max_temp_k=145.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'ArgonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.08, min_temp_k=80.0, max_temp_k=90.0, min_pressure_atm=None, max_pressure_atm=0.01, volcanism={'water'}),
            Ruleset(atmosphere={'CarbonDioxide', 'CarbonDioxideRich'}, body_types={'Rocky ice body', 'Icy body'}, star_types=None, min_gravity_g=0.25, max_gravity_g=0.32, min_temp_k=167.0, max_temp_k=240.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'Helium'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.49, max_gravity_g=0.53, min_temp_k=20.0, max_temp_k=21.0, min_pressure_atm=0.065, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'Neon'}, body_types={'Rocky ice body', 'Icy body'}, star_types=None, min_gravity_g=0.29, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=51.0, min_pressure_atm=None, max_pressure_atm=0.075, volcanism={'water'}),
            Ruleset(atmosphere={'NeonRich'}, body_types={'Rocky ice body', 'Icy body'}, star_types=None, min_gravity_g=0.43, max_gravity_g=0.61, min_temp_k=20.0, max_temp_k=65.0, min_pressure_atm=0.005, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.205, max_gravity_g=0.241, min_temp_k=60.0, max_temp_k=80.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'Oxygen'}, body_types={'Rocky ice body', 'Icy body'}, star_types=None, min_gravity_g=0.24, max_gravity_g=0.35, min_temp_k=154.0, max_temp_k=220.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.054, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        ],
    },
    "Cactoida": {
        "Cactoida Cortexum": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=197.0, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Cactoida Lapis": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        ],
        "Cactoida Vermis": [
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.265, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=210.0, min_pressure_atm=None, max_pressure_atm=0.005, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        ],
        "Cactoida Pullulanta": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=197.0, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Cactoida Peperatis": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        ],
    },
    "Clypeus": {
        "Clypeus Lacrimam": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=190.0, max_temp_k=None, min_pressure_atm=0.054, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        ],
        "Clypeus Margaritus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=190.0, max_temp_k=197.0, min_pressure_atm=0.054, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        ],
        "Clypeus Speculumi": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=190.0, max_temp_k=197.0, min_pressure_atm=0.055, max_pressure_atm=None, volcanism='none'),  # unmodeled: distance
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: distance
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),  # unmodeled: distance
        ],
    },
    "Concha": {
        "Concha Renibus": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.045, min_temp_k=176.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'silicate', 'metallic'}),
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=None, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Methane'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.15, min_temp_k=78.0, max_temp_k=100.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'silicate', 'metallic'}),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.65, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.65, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        ],
        "Concha Aureolas": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        ],
        "Concha Labiata": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=200.0, min_pressure_atm=0.002, max_pressure_atm=None, volcanism='none'),
        ],
        "Concha Biconcavis": [
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.053, max_gravity_g=0.275, min_temp_k=42.0, max_temp_k=52.0, min_pressure_atm=None, max_pressure_atm=0.0047, volcanism='none'),
        ],
    },
    "Electricae": {
        "Electricae Pluma": [
            Ruleset(atmosphere={'Argon', 'ArgonRich'}, body_types={'Icy body'}, star_types={'A', 'N', 'D', 'H', 'AeBe'}, min_gravity_g=0.025, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'Neon', 'NeonRich'}, body_types={'Icy body'}, star_types={'A', 'N', 'D', 'H', 'AeBe'}, min_gravity_g=0.26, max_gravity_g=0.276, min_temp_k=20.0, max_temp_k=70.0, min_pressure_atm=None, max_pressure_atm=0.005, volcanism=None),
        ],
        "Electricae Radialem": [
            Ruleset(atmosphere={'Argon', 'ArgonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: nebula
            Ruleset(atmosphere={'Neon', 'NeonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.026, max_gravity_g=0.276, min_temp_k=20.0, max_temp_k=70.0, min_pressure_atm=None, max_pressure_atm=0.005, volcanism=None),  # unmodeled: nebula
        ],
    },
    "Fonticulua": {
        "Fonticulua Segmentatus": [
            Ruleset(atmosphere={'Neon', 'NeonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.25, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=75.0, min_pressure_atm=None, max_pressure_atm=0.006, volcanism='none'),
        ],
        "Fonticulua Campestris": [
            Ruleset(atmosphere={'Argon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.027, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        ],
        "Fonticulua Upupam": [
            Ruleset(atmosphere={'ArgonRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.209, max_gravity_g=0.276, min_temp_k=61.0, max_temp_k=125.0, min_pressure_atm=0.0175, max_pressure_atm=None, volcanism=None),
        ],
        "Fonticulua Lapida": [
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.19, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=81.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        ],
        "Fonticulua Fluctus": [
            Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.235, max_gravity_g=0.276, min_temp_k=143.0, max_temp_k=200.0, min_pressure_atm=0.012, max_pressure_atm=None, volcanism=None),
        ],
        "Fonticulua Digitos": [
            Ruleset(atmosphere={'Methane'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.07, min_temp_k=83.0, max_temp_k=109.0, min_pressure_atm=0.03, max_pressure_atm=None, volcanism=None),
        ],
    },
    "Frutexa": {
        "Frutexa Flabellum": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        ],
        "Frutexa Acus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.237, min_temp_k=146.0, max_temp_k=197.0, min_pressure_atm=0.0029, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Frutexa Metallicum": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=176.0, min_pressure_atm=None, max_pressure_atm=0.01, volcanism='none'),
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=146.0, max_temp_k=197.0, min_pressure_atm=0.002, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Methane'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.05, max_gravity_g=0.1, min_temp_k=100.0, max_temp_k=300.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'Water'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.07, min_temp_k=None, max_temp_k=400.0, min_pressure_atm=None, max_pressure_atm=0.07, volcanism='none'),
        ],
        "Frutexa Flammasis": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        ],
        "Frutexa Fera": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=146.0, max_temp_k=197.0, min_pressure_atm=0.003, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Frutexa Sponsae": [
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.056, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.056, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        ],
        "Frutexa Collum": [
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=215.0, min_pressure_atm=None, max_pressure_atm=0.004, volcanism=None),
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.265, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=135.0, min_pressure_atm=None, max_pressure_atm=0.004, volcanism='none'),
        ],
    },
    "Fumerola": {
        "Fumerola Carbosis": [
            Ruleset(atmosphere={'Argon'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.168, max_gravity_g=0.276, min_temp_k=57.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon', 'methane'}),
            Ruleset(atmosphere={'Methane'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.047, min_temp_k=84.0, max_temp_k=110.0, min_pressure_atm=0.03, max_pressure_atm=None, volcanism={'methane magma'}),
            Ruleset(atmosphere={'Neon'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.26, max_gravity_g=0.276, min_temp_k=40.0, max_temp_k=60.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon', 'methane'}),
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.2, max_gravity_g=0.276, min_temp_k=57.0, max_temp_k=70.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon', 'methane'}),
            Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.26, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon'}),
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.185, max_gravity_g=0.276, min_temp_k=149.0, max_temp_k=272.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon', 'methane'}),
            Ruleset(atmosphere={'Ammonia', 'ArgonRich', 'CarbonDioxideRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=None, max_gravity_g=0.276, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'carbon'}),
        ],
        "Fumerola Extremus": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.09, min_temp_k=161.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism={'silicate', 'metallic', 'rocky'}),
            Ruleset(atmosphere={'Argon'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.07, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=121.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'silicate', 'metallic', 'rocky'}),
            Ruleset(atmosphere={'Methane'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.127, min_temp_k=77.0, max_temp_k=109.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'silicate', 'metallic', 'rocky'}),
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.07, max_gravity_g=0.276, min_temp_k=54.0, max_temp_k=210.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'silicate', 'metallic', 'rocky'}),
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.05, max_gravity_g=0.276, min_temp_k=500.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'silicate', 'metallic', 'rocky'}),
        ],
        "Fumerola Nitris": [
            Ruleset(atmosphere={'Neon'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=30.0, max_temp_k=129.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'Argon', 'ArgonRich', 'NeonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.044, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=141.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'Methane'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.025, max_gravity_g=0.1, min_temp_k=83.0, max_temp_k=109.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'nitrogen'}),
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.21, max_gravity_g=0.276, min_temp_k=60.0, max_temp_k=81.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=None, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.21, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=250.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'nitrogen', 'ammonia'}),
        ],
        "Fumerola Aquatis": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Icy body', 'Rocky ice body', 'Rocky body'}, star_types=None, min_gravity_g=0.028, max_gravity_g=0.276, min_temp_k=161.0, max_temp_k=177.0, min_pressure_atm=0.002, max_pressure_atm=0.02, volcanism={'water'}),
            Ruleset(atmosphere={'Argon', 'ArgonRich'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.166, max_gravity_g=0.276, min_temp_k=57.0, max_temp_k=150.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.25, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=0.01, max_pressure_atm=0.03, volcanism={'water'}),
            Ruleset(atmosphere={'Methane'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=80.0, max_temp_k=100.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'Neon'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.26, max_gravity_g=0.276, min_temp_k=20.0, max_temp_k=60.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.195, max_gravity_g=0.245, min_temp_k=56.0, max_temp_k=80.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.276, min_temp_k=153.0, max_temp_k=190.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Icy body', 'Rocky ice body', 'Rocky body'}, star_types=None, min_gravity_g=0.18, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=270.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.06, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        ],
    },
    "Fungoida": {
        "Fungoida Setisis": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
            Ruleset(atmosphere={'Methane'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.033, max_gravity_g=0.276, min_temp_k=68.0, max_temp_k=109.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Methane'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.033, max_gravity_g=0.276, min_temp_k=67.0, max_temp_k=109.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        ],
        "Fungoida Stabitis": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.045, min_temp_k=172.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'silicate'}),  # unmodeled: regions
            Ruleset(atmosphere={'Argon'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.20, max_gravity_g=0.23, min_temp_k=60.0, max_temp_k=90.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'silicate', 'rocky'}),  # unmodeled: regions
            Ruleset(atmosphere={'ArgonRich'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.3, max_gravity_g=0.5, min_temp_k=60.0, max_temp_k=90.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.0405, max_gravity_g=0.27, min_temp_k=180.0, max_temp_k=None, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
            Ruleset(atmosphere={'Methane'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.043, max_gravity_g=0.126, min_temp_k=78.5, max_temp_k=109.0, min_pressure_atm=0.012, max_pressure_atm=None, volcanism={'major silicate'}),  # unmodeled: regions
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.039, max_gravity_g=0.064, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Fungoida Bullarum": [
            Ruleset(atmosphere={'Argon'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.058, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=129.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.155, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=70.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        ],
        "Fungoida Gelata": [
            Ruleset(atmosphere={'Argon'}, body_types={'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.041, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism={'major silicate'}),  # unmodeled: regions
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.071, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism={'major silicate'}),  # unmodeled: regions
            Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.071, min_temp_k=160.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism={'major rocky'}),  # unmodeled: regions
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.041, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=None, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
            Ruleset(atmosphere={'Methane'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.044, max_gravity_g=0.125, min_temp_k=80.0, max_temp_k=110.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'major silicate', 'major metallic'}),  # unmodeled: regions
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.039, max_gravity_g=0.063, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
    },
    "Osseus": {
        "Osseus Fractus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=None, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Osseus Discus": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.088, min_temp_k=161.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism='any'),
            Ruleset(atmosphere={'Argon'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.2, max_gravity_g=0.276, min_temp_k=65.0, max_temp_k=120.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.026, max_gravity_g=0.276, min_temp_k=500.0, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'Methane'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.127, min_temp_k=80.0, max_temp_k=110.0, min_pressure_atm=0.012, max_pressure_atm=None, volcanism='any'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.055, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        ],
        "Osseus Spiralis": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=160.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        ],
        "Osseus Pumice": [
            Ruleset(atmosphere={'Argon'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.059, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=135.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Argon'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.059, max_gravity_g=0.276, min_temp_k=50.0, max_temp_k=135.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water', 'geysers'}),
            Ruleset(atmosphere={'ArgonRich'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.035, max_gravity_g=0.276, min_temp_k=60.0, max_temp_k=80.5, min_pressure_atm=0.03, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Methane'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.033, max_gravity_g=0.276, min_temp_k=67.0, max_temp_k=109.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'Nitrogen'}, body_types={'Rocky body', 'Rocky ice body', 'High metal content body'}, star_types=None, min_gravity_g=0.05, max_gravity_g=0.276, min_temp_k=42.0, max_temp_k=70.1, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        ],
        "Osseus Cornibus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.0405, max_gravity_g=0.276, min_temp_k=180.0, max_temp_k=None, min_pressure_atm=0.025, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Osseus Pellebantus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.0405, max_gravity_g=0.276, min_temp_k=191.0, max_temp_k=None, min_pressure_atm=0.057, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
    },
    "Recepta": {
        "Recepta Umbrux": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types=None, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=151.0, max_temp_k=200.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: atmosphere_component
            Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.276, min_temp_k=154.0, max_temp_k=175.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='none'),  # unmodeled: atmosphere_component
            Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.276, min_temp_k=154.0, max_temp_k=175.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'water'}),  # unmodeled: atmosphere_component
            Ruleset(atmosphere={'SulphurDioxide'}, body_types=None, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=273.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: atmosphere_component
        ],
        "Recepta Deltahedronix": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types=None, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=195.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: atmosphere_component
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Icy body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=195.0, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),  # unmodeled: atmosphere_component
            Ruleset(atmosphere={'SulphurDioxide'}, body_types=None, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=272.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: atmosphere_component
        ],
        "Recepta Conditivus": [
            Ruleset(atmosphere={'CarbonDioxide', 'CarbonDioxideRich'}, body_types={'Icy body', 'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=150.0, max_temp_k=195.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: atmosphere_component
            Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.276, min_temp_k=154.0, max_temp_k=175.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='none'),  # unmodeled: atmosphere_component
            Ruleset(atmosphere={'Oxygen'}, body_types={'Icy body'}, star_types=None, min_gravity_g=0.23, max_gravity_g=0.276, min_temp_k=154.0, max_temp_k=175.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism={'water'}),  # unmodeled: atmosphere_component
            Ruleset(atmosphere={'SulphurDioxide'}, body_types=None, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=275.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: atmosphere_component
        ],
    },
    "Stratum": {
        "Stratum Excutitus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.48, min_temp_k=165.0, max_temp_k=190.0, min_pressure_atm=0.0035, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.4, min_temp_k=165.0, max_temp_k=190.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
        ],
        "Stratum Paleas": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.35, min_temp_k=165.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.585, min_temp_k=165.0, max_temp_k=395.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'CarbonDioxideRich'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.43, max_gravity_g=0.585, min_temp_k=185.0, max_temp_k=260.0, min_pressure_atm=0.015, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.056, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.056, min_temp_k=None, max_temp_k=None, min_pressure_atm=0.065, max_pressure_atm=None, volcanism={'water'}),
            Ruleset(atmosphere={'Oxygen'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.39, max_gravity_g=0.59, min_temp_k=165.0, max_temp_k=250.0, min_pressure_atm=0.022, max_pressure_atm=None, volcanism=None),
        ],
        "Stratum Laminamus": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.34, min_temp_k=165.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        ],
        "Stratum Araneamus": [
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.26, max_gravity_g=0.57, min_temp_k=165.0, max_temp_k=373.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        ],
        "Stratum Limaxus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.03, max_gravity_g=0.4, min_temp_k=165.0, max_temp_k=190.0, min_pressure_atm=0.05, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.27, max_gravity_g=0.4, min_temp_k=165.0, max_temp_k=190.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
        ],
        "Stratum Cucumisis": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.6, min_temp_k=191.0, max_temp_k=371.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
            Ruleset(atmosphere={'CarbonDioxideRich'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.44, max_gravity_g=0.56, min_temp_k=210.0, max_temp_k=246.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
            Ruleset(atmosphere={'Oxygen'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.6, min_temp_k=200.0, max_temp_k=250.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.26, max_gravity_g=0.55, min_temp_k=191.0, max_temp_k=373.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
        ],
        "Stratum Tectonicas": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.38, min_temp_k=165.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'Argon', 'ArgonRich'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.485, max_gravity_g=0.54, min_temp_k=167.0, max_temp_k=199.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.61, min_temp_k=165.0, max_temp_k=430.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'CarbonDioxideRich'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.035, max_gravity_g=0.61, min_temp_k=165.0, max_temp_k=260.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'Oxygen'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.4, max_gravity_g=0.52, min_temp_k=165.0, max_temp_k=246.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.29, max_gravity_g=0.62, min_temp_k=165.0, max_temp_k=450.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'Water'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.063, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        ],
        "Stratum Frigus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.043, max_gravity_g=0.54, min_temp_k=191.0, max_temp_k=365.0, min_pressure_atm=0.001, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
            Ruleset(atmosphere={'CarbonDioxideRich'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.45, max_gravity_g=0.56, min_temp_k=200.0, max_temp_k=250.0, min_pressure_atm=0.01, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.29, max_gravity_g=0.52, min_temp_k=191.0, max_temp_k=369.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),  # unmodeled: regions
        ],
    },
    "Tubus": {
        "Tubus Conifer": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.041, max_gravity_g=0.153, min_temp_k=160.0, max_temp_k=197.0, min_pressure_atm=0.003, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Tubus Sororibus": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.152, min_temp_k=160.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'High metal content body'}, star_types=None, min_gravity_g=0.045, max_gravity_g=0.152, min_temp_k=160.0, max_temp_k=195.0, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
        ],
        "Tubus Cavas": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.152, min_temp_k=160.0, max_temp_k=197.0, min_pressure_atm=0.003, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Tubus Rosarium": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.153, min_temp_k=160.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),
        ],
        "Tubus Compagibus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.153, min_temp_k=160.0, max_temp_k=197.0, min_pressure_atm=0.003, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
    },
    "Tussock": {
        "Tussock Pennata": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.09, min_temp_k=146.0, max_temp_k=154.0, min_pressure_atm=0.00289, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Tussock Ventusa": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.13, min_temp_k=155.0, max_temp_k=160.0, min_pressure_atm=0.00289, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Tussock Ignis": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.2, min_temp_k=161.0, max_temp_k=170.0, min_pressure_atm=0.00289, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Tussock Cultro": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        ],
        "Tussock Catena": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        ],
        "Tussock Pennatis": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=147.0, max_temp_k=197.0, min_pressure_atm=0.00289, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Tussock Serrati": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.23, min_temp_k=171.0, max_temp_k=174.0, min_pressure_atm=0.01, max_pressure_atm=0.071, volcanism='none'),  # unmodeled: regions
        ],
        "Tussock Albata": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.276, min_temp_k=175.0, max_temp_k=180.0, min_pressure_atm=0.016, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Tussock Propagito": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=145.0, max_temp_k=197.0, min_pressure_atm=0.00289, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Tussock Divisa": [
            Ruleset(atmosphere={'Ammonia'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.042, max_gravity_g=0.276, min_temp_k=152.0, max_temp_k=177.0, min_pressure_atm=None, max_pressure_atm=0.0135, volcanism=None),  # unmodeled: regions
        ],
        "Tussock Caputus": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.041, max_gravity_g=0.27, min_temp_k=181.0, max_temp_k=190.0, min_pressure_atm=0.0275, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Tussock Triticum": [
            Ruleset(atmosphere={'CarbonDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=191.0, max_temp_k=197.0, min_pressure_atm=0.058, max_pressure_atm=None, volcanism='none'),  # unmodeled: regions
        ],
        "Tussock Stigmasis": [
            Ruleset(atmosphere={'SulphurDioxide'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.276, min_temp_k=132.0, max_temp_k=180.0, min_pressure_atm=None, max_pressure_atm=0.01, volcanism=None),
        ],
        "Tussock Virgam": [
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.065, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism='none'),
            Ruleset(atmosphere={'Water'}, body_types={'Rocky body', 'High metal content body'}, star_types=None, min_gravity_g=0.04, max_gravity_g=0.065, min_temp_k=None, max_temp_k=None, min_pressure_atm=None, max_pressure_atm=None, volcanism={'water'}),
        ],
        "Tussock Capillum": [
            Ruleset(atmosphere={'Argon'}, body_types={'Rocky ice body'}, star_types=None, min_gravity_g=0.22, max_gravity_g=0.276, min_temp_k=80.0, max_temp_k=129.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
            Ruleset(atmosphere={'Methane'}, body_types={'Rocky body', 'Rocky ice body'}, star_types=None, min_gravity_g=0.033, max_gravity_g=0.276, min_temp_k=80.0, max_temp_k=110.0, min_pressure_atm=None, max_pressure_atm=None, volcanism=None),
        ],
    },
}
