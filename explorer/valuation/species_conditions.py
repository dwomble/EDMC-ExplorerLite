""" Per-species spawn conditions, narrowing genus_conditions.py's genus-level guesses down to a
specific species (e.g. "Tussock Ignis" vs "Tussock Pennata" by temperature band). Scoped to
atmosphere-bearing genera only -- airless genera stay genus-only via GENUS_RULESETS. Reuses
genus_conditions.py's `Ruleset` dataclass and sourcing policy. Species names must match
exobiology_data.py's SPECIES_VALUE keys exactly. Data lives in data/species_rulesets.json. """
from explorer.valuation.genus_conditions import Ruleset, load_json, rulesets_from_json

SPECIES_RULESETS:dict[str, dict[str, list[Ruleset]]] = {
    genus: {species: rulesets_from_json(entries) for species, entries in by_species.items()}
    for genus, by_species in load_json('species_rulesets.json').items()
}
