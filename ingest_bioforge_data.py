#!/usr/bin/env python3

"""Use sample data from Canonn Bioforge to update species region requirements"""

import json
import sys
import urllib.request

SAMPLES_URL = "https://github.com/canonn-science/bioforge/raw/refs/heads/main/data/samples.json"

if __name__ == "__main__":
    if len(sys.argv) < 3 or "--help" in sys.argv:
        print(f"{sys.argv[0]} - download canonn bioforge sample data and update species region requirements\n")
        print(f"usage: {sys.argv[0]} <path to genus_rulesets.json> <path to species_rulesets.json>")
        sys.exit(1)

    print(f"fetching sample data from {SAMPLES_URL}...")
    with urllib.request.urlopen(SAMPLES_URL) as samples:
        samples = json.load(samples)

    print(f"loading existing genus rulesets from {sys.argv[1]}...")
    with open(sys.argv[1], "r") as genus_rulesets:
        genus_rulesets = json.load(genus_rulesets)

    print(f"loading existing species rulesets from {sys.argv[2]}...")
    with open(sys.argv[2], "r") as species_rulesets:
        species_rulesets = json.load(species_rulesets)

    print("updating rulesets...")
    regions = samples["regions"]
    for species in samples["species"]:
        possible_regions = [regions[i] for i, r in enumerate(species["regions"]) if r > 0]

        for ruleset in genus_rulesets[species["g"]]:
            ruleset["regions"] = list(set(possible_regions) | set(ruleset.get("regions", [])))
        
        if species["g"] not in species_rulesets:
            continue

        for ruleset in species_rulesets[species["g"]][species["s"]]:
            ruleset["regions"] = possible_regions

    with open(sys.argv[1], "w") as genus_rulesets_file:
        json.dump(genus_rulesets, genus_rulesets_file, indent = 2)
    with open(sys.argv[2], "w") as species_rulesets_file:
        json.dump(species_rulesets, species_rulesets_file, indent = 2)
    print("done!")
