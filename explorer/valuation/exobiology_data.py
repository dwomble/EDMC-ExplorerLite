"""
Static exobiology reference data: per-genus minimum sample distance, and per-genus/species
base credit values (excluding first-discovery/first-logged bonus). Clean-room, sourced from
the Elite Dangerous Fandom wiki's "Exobiology Sample Values and Details" page, cross-checked
against njthomson/SrvSurvey's "Organic Scanning" reference (independent source, matched
exactly on every genus/distance) -- see REQUIREMENTS.md for the licensing rationale (keeps
this plugin permissively licensed, no GPL entanglement with BioScan's data).

Deliberately excluded: Thargoid biologicals (Spires, Mega Barnacles, Coral Tree, Coral Root) --
tied to Thargoid structure sites rather than ordinary planetary exploration, and it's
unconfirmed whether they even use the same ScanOrganic/Genetic-Sampler mechanic. Out of scope
for a general exploration assistant; revisit if that changes.

CAVEAT: the exact in-game `Genus_Localised` string for three genera (singular vs. plural) is
unconfirmed -- "Sinuous Tuber(s)", "Bark Mound(s)", "Crystalline Shard(s)". The Fandom wiki
titles them singular; a tool that parses live journals (SrvSurvey) uses plural. Singular is
used below as the dict key; verify against a real captured journal line and correct if needed.
"""

# Minimum distance (meters) required between exobiology samples of the same genus.
GENUS_MIN_DISTANCE_M:dict[str, int] = {
    "Aleoida": 150,
    "Amphora Plant": 100,
    "Anemone": 100,
    "Bacterium": 500,
    "Bark Mound": 100, # CAVEAT: plurality of Genus_Localised unconfirmed, see module docstring
    "Brain Tree": 100,
    "Cactoida": 300,
    "Clypeus": 150,
    "Concha": 150,
    "Crystalline Shard": 100, # CAVEAT: plurality of Genus_Localised unconfirmed, see module docstring
    "Electricae": 1000,
    "Fonticulua": 500,
    "Frutexa": 150,
    "Fumerola": 100,
    "Fungoida": 300,
    "Osseus": 800,
    "Recepta": 150,
    "Sinuous Tuber": 100, # CAVEAT: plurality of Genus_Localised unconfirmed, see module docstring
    "Stratum": 500,
    "Tubus": 800,
    "Tussock": 200,
}

# Per-species base credit value (excluding first-discovery/first-logged bonus), keyed by
# genus -> {species_full_name: credits}.
SPECIES_VALUE:dict[str, dict[str, int]] = {
    "Aleoida": {
        "Aleoida Arcus": 7_252_500,
        "Aleoida Coronamus": 6_284_600,
        "Aleoida Gravis": 12_934_900,
        "Aleoida Laminiae": 3_385_200,
        "Aleoida Spica": 3_385_200,
    },
    "Amphora Plant": {
        "Amphora Plant": 3_626_400,
    },
    "Anemone": {
        "Anemone Blatteum Bioluminescent": 1_499_900,
        "Anemone Croceum": 3_399_800,
        "Anemone Luteolum": 1_499_900,
        "Anemone Prasinum Bioluminescent": 1_499_900,
        "Anemone Puniceum": 1_499_900,
        "Anemone Roseum": 1_499_900,
        "Anemone Roseum Bioluminescent": 1_499_900,
        "Anemone Rubeum Bioluminescent": 1_499_900,
    },
    "Bacterium": {
        "Bacterium Nebulus": 9_116_600,
        "Bacterium Acies": 1_000_000,
        "Bacterium Omentum": 4_638_900,
        "Bacterium Scopulum": 8_633_800,
        "Bacterium Verrata": 3_897_000,
        "Bacterium Bullaris": 1_152_500,
        "Bacterium Vesicula": 1_000_000,
        "Bacterium Informem": 8_418_000,
        "Bacterium Volu": 7_774_700,
        "Bacterium Alcyoneum": 1_658_500,
        "Bacterium Aurasus": 1_000_000,
        "Bacterium Cerbrus": 1_689_800,
        "Bacterium Tela": 1_949_000,
    },
    "Bark Mound": {
        "Bark Mound": 1_471_900,
    },
    "Brain Tree": {
        "Brain Tree Aureum": 3_565_100,
        "Brain Tree Gypseeum": 3_565_100,
        "Brain Tree Lindigoticum": 3_565_100,
        "Brain Tree Lividum": 1_593_700,
        "Brain Tree Ostrinum": 3_565_100,
        "Brain Tree Puniceum": 3_565_100,
        "Brain Tree Roseum": 1_593_700,
        "Brain Tree Viride": 1_593_700,
    },
    "Cactoida": {
        "Cactoida Cortexum": 3_667_600,
        "Cactoida Lapis": 2_483_600,
        "Cactoida Peperatis": 2_483_600,
        "Cactoida Pullulanta": 3_667_600,
        "Cactoida Vermis": 16_202_800,
    },
    "Clypeus": {
        "Clypeus Lacrimam": 8_418_000,
        "Clypeus Margaritus": 11_873_200,
        "Clypeus Speculumi": 16_202_800,
    },
    "Concha": {
        "Concha Aureolas": 7_774_700,
        "Concha Biconcavis": 16_777_215,
        "Concha Labiata": 2_352_400,
        "Concha Renibus": 4_572_400,
    },
    "Crystalline Shard": {
        "Crystalline Shard": 3_626_400,
    },
    "Electricae": {
        "Electricae Pluma": 6_284_600,
        "Electricae Radialem": 6_284_600,
    },
    "Fonticulua": {
        "Fonticulua Campestris": 1_000_000,
        "Fonticulua Digitos": 1_804_100,
        "Fonticulua Fluctus": 20_000_000, # corrected from 16,777,215 -- multiple sources (incl. BioScan) agree on 20M
        "Fonticulua Lapida": 3_111_000,
        "Fonticulua Segmentatus": 19_010_800,
        "Fonticulua Upupam": 5_727_600,
    },
    "Frutexa": {
        "Frutexa Acus": 7_774_700,
        "Frutexa Collum": 1_639_800,
        "Frutexa Fera": 1_632_500,
        "Frutexa Flabellum": 1_808_900,
        "Frutexa Flammasis": 10_326_000,
        "Frutexa Metallicum": 1_632_500,
        "Frutexa Sponsae": 5_988_000,
    },
    "Fumerola": {
        "Fumerola Aquatis": 6_284_600,
        "Fumerola Carbosis": 6_284_600,
        "Fumerola Extremus": 16_202_800,
        "Fumerola Nitris": 7_500_900,
    },
    "Fungoida": {
        "Fungoida Bullarum": 3_703_200,
        "Fungoida Gelata": 3_330_300,
        "Fungoida Setisis": 1_670_100,
        "Fungoida Stabitis": 2_680_300,
    },
    "Osseus": {
        "Osseus Cornibus": 1_483_000,
        "Osseus Discus": 12_934_900,
        "Osseus Fractus": 4_027_800,
        "Osseus Pellebantus": 9_739_000,
        "Osseus Pumice": 3_156_300,
        "Osseus Spiralis": 2_404_700,
    },
    "Recepta": {
        "Recepta Conditivus": 14_313_700,
        "Recepta Deltahedronix": 16_202_800,
        "Recepta Umbrux": 12_934_900,
    },
    "Sinuous Tuber": {
        "Sinuous Tuber Albidum": 3_425_600,
        "Sinuous Tuber Blatteum": 1_514_500,
        "Sinuous Tuber Caeruleum": 1_514_500,
        "Sinuous Tuber Lindigoticum": 1_514_500,
        "Sinuous Tuber Prasinum": 1_514_500,
        "Sinuous Tuber Roseus": 1_514_500,
        "Sinuous Tuber Violaceum": 1_514_500,
        "Sinuous Tuber Viride": 1_514_500,
    },
    "Stratum": {
        "Stratum Araneamus": 2_448_900,
        "Stratum Cucumisis": 16_202_800,
        "Stratum Excutitus": 2_448_900,
        "Stratum Frigus": 2_637_500,
        "Stratum Laminamus": 2_788_300,
        "Stratum Limaxus": 1_362_000,
        "Stratum Paleas": 1_362_000,
        "Stratum Tectonicas": 19_010_800,
    },
    "Tubus": {
        "Tubus Cavas": 11_873_200,
        "Tubus Compagibus": 7_774_700,
        "Tubus Conifer": 2_415_500,
        "Tubus Rosarium": 2_637_500,
        "Tubus Sororibus": 5_727_600,
    },
    "Tussock": {
        "Tussock Albata": 3_252_500,
        "Tussock Capillum": 7_025_800,
        "Tussock Caputus": 3_472_400,
        "Tussock Catena": 1_766_600,
        "Tussock Cultro": 1_766_600,
        "Tussock Divisa": 1_766_600,
        "Tussock Ignis": 1_849_000,
        "Tussock Pennata": 5_853_800,
        "Tussock Pennatis": 1_000_000,
        "Tussock Propagito": 1_000_000,
        "Tussock Serrati": 4_447_100,
        "Tussock Stigmasis": 19_010_800,
        "Tussock Triticum": 7_774_700,
        "Tussock Ventusa": 3_277_700,
        "Tussock Virgam": 14_313_700,
    },
}

# Confirmed: total payout for a first-logged sample = base value x 5 (i.e. base + 4x bonus).
FIRST_LOGGED_BONUS_MULTIPLIER:int = 5

def genus_min_distance(genus:str) -> int|None:
    return GENUS_MIN_DISTANCE_M.get(genus)

def genus_value_range(genus:str) -> tuple[int, int]|None:
    """ (min, max) base credit value across all known species of a genus, or None if unknown. """
    species:dict[str, int]|None = SPECIES_VALUE.get(genus)
    if not species:
        return None
    values:list[int] = list(species.values())
    return (min(values), max(values))

def species_value(genus:str, species:str) -> int|None:
    return SPECIES_VALUE.get(genus, {}).get(species)
