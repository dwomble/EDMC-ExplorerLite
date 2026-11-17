#!/usr/bin/env python3

"""Use sample data from Canonn Bioforge to update species region requirements"""

import json
import sys
import urllib.request

SAMPLES_URL = "https://github.com/canonn-science/bioforge/raw/refs/heads/main/data/samples.json"

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(f"{sys.argv[0]} - download canonn bioforge sample data and update species region requirements\n")
        print(f"usage: {sys.argv[0]} <path to species_rulesets.json>")
        sys.exit(1)

    print(f"fetching sample data from {SAMPLES_URL}...")
    with urllib.request.urlopen(SAMPLES_URL) as samples:
        samples = json.load(samples)

    print(f"loading existing species rulesets from {sys.argv[1]}...")
    with open(sys.argv[1], "r") as rulesets:
        rulesets = json.load(rulesets)

    print("updating rulesets...")
    regions = samples["regions"]
    for species in samples["species"]:
        if species["g"] not in rulesets:
            continue

        possible_regions = [regions[i] for i, r in enumerate(species["regions"]) if r > 0]
        for ruleset in rulesets[species["g"]][species["s"]]:
            ruleset["regions"] = possible_regions
            if ruleset.get("unmodeled") == "regions":
                del ruleset["unmodeled"]

    with open(sys.argv[1], "w") as rulesets_file:
        json.dump(rulesets, rulesets_file, indent = 2)
    print("done!")
