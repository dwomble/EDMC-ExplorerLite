"""Look up the galactic region for systems"""

# Copied & modified from https://github.com/klightspeed/EliteDangerousRegionMap/blob/master/RegionMap.py
# Original license:
#
# MIT License
# 
# Copyright (c) 2020 Ben Peddell
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import time
from pathlib import Path

from config import config, user_agent # type: ignore
from timeout_session import new_session # type: ignore

from explorer.constants import GH_PROJECT
from explorer.utils.debug import Debug
from explorer.valuation.genus_conditions import load_json

SAMPLES_URL:str = "https://github.com/canonn-science/bioforge/raw/refs/heads/main/data/samples.json"
REFRESH_INTERVAL:int = 7 * 24 * 3600
TIMEOUT:int = 30
NAMES:dict[str, str] = {"Bark Mounds": "Bark Mound", "Crystalline Shards": "Crystalline Shard", "Sinuous Tubers": "Sinuous Tuber",
                        "The Formidine Rift": "Formidine Rift"}

def _local_path() -> Path:
    """ Refreshed copy, kept out of plugin_dir so a reinstall doesn't lose it. """
    return Path(config.app_dir_path) / GH_PROJECT / "data" / "species_regions.json"

_MAP:dict = load_json('RegionMapData.json')
REGIONS:list[str|None] = _MAP['regions']
REGION_MAP:list[list[list[int]]] = _MAP['regionmap']
SPECIES_REGIONS:dict[str, dict[str, list[str]]] = \
    json.loads(_local_path().read_text()) if _local_path().exists() else load_json('species_regions.json')

x0 = -49985
y0 = -40985
z0 = -24105

def find_region(x:float, y:float, z:float) -> str|None:
    """Get the name of the galactic region for the given position."""

    px = int((x - x0) * 83 / 4096)
    pz = int((z - z0) * 83 / 4096)

    if px < 0 or pz < 0 or pz >= len(REGION_MAP):
        return None
    else:
        row = REGION_MAP[pz]
        rx = 0

        for rl, pv in row:
            if px < rx + rl:
                break
            else:
                rx += rl
        else:
            pv = 0

        if pv == 0:
            return None
        else:
            return REGIONS[pv]

def allowed(name:str, region:str|None) -> bool:
    """ Whether a species (or single-species genus) can occur in region; unknown regions allow everything. """
    limits:dict|None = SPECIES_REGIONS.get(name)
    if region is None or not limits: return True
    if "allowed" in limits: return region in limits["allowed"]
    return region not in limits["excluded"]

def refresh() -> None:
    """ Rebuild the species region limits from Canonn Bioforge's samples, at most once per REFRESH_INTERVAL. """
    global SPECIES_REGIONS
    key:str = f"{GH_PROJECT}_regions_refreshed"
    if config.get_int(key, 0) >= int(time.time()) - REFRESH_INTERVAL: return

    try:
        resp = new_session(timeout=TIMEOUT).get(SAMPLES_URL, headers={'User-Agent': f'{user_agent} {GH_PROJECT}'}, timeout=TIMEOUT)
        resp.raise_for_status()
        samples:dict = resp.json()

        names:list[str] = [NAMES.get(r) or r for r in samples["regions"]]
        limits:dict[str, dict[str, list[str]]] = {}
        for species in samples["species"]:
            seen:list[str] = [r for r, share in zip(names, species["regions"]) if share > 0]
            if len(seen) == len(names): continue

            excluded:list[str] = [r for r in names if r not in seen]
            limits[NAMES.get(species["s"]) or species["s"]] = {"allowed": seen} if len(seen) <= len(excluded) else {"excluded": excluded}
        if not limits: raise ValueError("no region-limited species in Canonn samples")
    except Exception as e:
        Debug.logger.error("Failed to refresh Canonn region data, exception info:", exc_info=e)
        return

    path:Path = _local_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    rows:list[str] = [f'  {json.dumps(name)}: {json.dumps(limits[name])}' for name in sorted(limits)]
    path.with_suffix(".tmp").write_text("{\n" + ",\n".join(rows) + "\n}\n")
    path.with_suffix(".tmp").replace(path)

    SPECIES_REGIONS = limits
    config.set(key, int(time.time()))
    Debug.logger.info(f"Refreshed region limits for {len(limits)} species")
