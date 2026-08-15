"""
Exobiology handlers: ScanOrganic (per-sample progress), SellOrganicData (actual credits
earned, ground truth), and CodexEntry (waypoint-tagging a species you've spotted but aren't
currently sampling).
"""
import json
import sqlite3

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.util import now_iso, surface_distance_m
from explorer.valuation import exobiology, exobiology_data

# Confirmed against real captured journal lines (2026-07 sessions): every completed species
# follows exactly ScanType Log -> Sample -> Sample -> Analyse, in that order -- Log and the two
# Samples are the 3 real genetic samples; Analyse is a separate finalize/submit step seconds
# later at the same location, not a 4th sample. Only Log/Sample increment samples_taken;
# Analyse just marks completion.
SAMPLE_SCAN_TYPES = ("Log", "Sample")

CODEX_ORGANIC_SUBCATEGORY = "$Codex_SubCategory_Organic_Structures;"

def _discard_tags_within_min_distance(state:ExplorerState, genus:str, lat:float, lon:float) -> None:
    """ A real sample invalidates any existing codex-tagged waypoint for the same genus that's
    now within the genus's minimum sample distance -- ED requires same-genus samples to be
    spaced at least that far apart, so a tag that close can no longer yield a valid additional
    sample. Leaving it on the radar would send you somewhere pointless. """
    if state.planet_radius is None:
        return
    min_dist:int|None = exobiology_data.genus_min_distance(genus)
    if min_dist is None:
        return
    positions:list|None = state.sample_positions.get(genus)
    if not positions:
        return
    state.sample_positions[genus] = [
        p for p in positions
        if p[2] is None or surface_distance_m(lat, lon, p[0], p[1], state.planet_radius) >= min_dist
    ]

def _too_close_to_existing_sample(state:ExplorerState, genus:str, lat:float, lon:float) -> bool:
    """ Mirror check for a brand-new tag: don't add a waypoint that's already within the
    genus's minimum sample distance of a real sample already taken -- it would be unusable
    from the moment it appeared. """
    if state.planet_radius is None:
        return False
    min_dist:int|None = exobiology_data.genus_min_distance(genus)
    if min_dist is None:
        return False
    return any(
        p[2] is None and surface_distance_m(lat, lon, p[0], p[1], state.planet_radius) < min_dist
        for p in state.sample_positions.get(genus, [])
    )

def on_scan_organic(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None or state.cmdr_id is None:
        return {}
    body_id:int|None = entry.get("Body")
    if body_id is None:
        return {}
    body_name:str = state.body_name if state.body_id == body_id else ""
    body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, body_id, body_name)

    genus:str = entry.get("Genus_Localised") or entry.get("Genus", "")
    species:str = entry.get("Species_Localised") or entry.get("Species", "")
    variant:str = entry.get("Variant_Localised") or entry.get("Variant", "")
    scan_type:str = entry.get("ScanType", "")

    progress_id:int = store.get_or_create_species_progress(body_pk, genus)
    row:sqlite3.Row|None = store.get_species_progress_row(progress_id)
    now:str = now_iso()

    fields:dict = dict(species=species, variant=variant, last_stage=scan_type)

    if scan_type in SAMPLE_SCAN_TYPES:
        fields["samples_taken"] = (row["samples_taken"] if row else 0) + 1
        fields["last_sample_at"] = now
        if not row or not row["first_sample_at"]:
            fields["first_sample_at"] = now

        # ScanOrganic itself carries no position -- capture the dashboard's latest lat/long as
        # this sample's position (for the overlay radar's per-sample markers, session-only,
        # see state.py). Only for real samples, not the Analyse finalize step.
        state.current_genus = genus # the radar's one active ring belongs to whichever genus you're actually sampling
        if state.has_lat_long and state.latitude is not None and state.longitude is not None:
            state.sample_positions.setdefault(genus, []).append((state.latitude, state.longitude, None)) # None -- a real sample, not a color-coded tag
            _discard_tags_within_min_distance(state, genus, state.latitude, state.longitude)
    elif scan_type == "Analyse" and (not row or not row["completed_at"]):
        fields["completed_at"] = now

    confirmed_value:int|None = exobiology.estimate_confirmed_value(genus, species)
    if confirmed_value is not None:
        fields["confirmed_value"] = confirmed_value

    store.update_species_progress(progress_id, **fields)
    return {"panel": True, "overlay": "radar"}

def on_codex_entry(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    """ The low-altitude composition scanner (ship or SRV) fires this whenever it identifies a
    biological signal -- for genuinely new discoveries AND re-scans of already-known ones alike
    -- carrying an exact Latitude/Longitude, unlike SAASignalsFound's aggregate genus+count.
    Useful for tagging a waypoint to a species you've spotted but aren't currently sampling (e.g.
    scanning something else nearby). Reuses state.sample_positions -- the same session-only,
    radar-only store ScanOrganic feeds -- so it gets a ring + dot immediately, without touching
    samples_taken/species_progress completion, so it's never mistaken for a real genetic sample
    in the panel's progress counts. Name_Localised also gives the exact SPECIES (not just
    genus), so it confirms the species/value the same way a real sample eventually would --
    replacing whatever "possible species" guess was showing, well before you land and sample it.
    Its color variant (e.g. "Tussock Cultro - Yellow") is stashed alongside the position too, so
    the radar can draw it in that color instead of the plain sample-taken blue -- these are
    passive tags, not "currently working on it", and looked identical to real samples otherwise.
    A tag within the genus's minimum sample distance of a real sample already taken is never
    even added as a waypoint -- it couldn't produce a valid additional sample (see
    _too_close_to_existing_sample), so it'd just be sending you somewhere pointless. """
    if entry.get("SubCategory") != CODEX_ORGANIC_SUBCATEGORY:
        return {}
    if state.system_id is None or state.cmdr_id is None:
        return {}
    body_id:int|None = entry.get("BodyID")
    latitude:float|None = entry.get("Latitude")
    longitude:float|None = entry.get("Longitude")
    if body_id is None or latitude is None or longitude is None:
        return {}
    name_parts:list[str] = entry.get("Name_Localised", "").split(" - ", 1)
    species:str = name_parts[0].strip()
    color_name:str|None = name_parts[1].strip() if len(name_parts) > 1 else None
    genus:str|None = exobiology_data.genus_from_species_name(species)
    if genus is None:
        return {}

    body_name:str = state.body_name if state.body_id == body_id else ""
    body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, body_id, body_name)
    progress_id:int = store.get_or_create_species_progress(body_pk, genus) # ensures it shows even before/without SAASignalsFound

    fields:dict = dict(species=species)
    confirmed_value:int|None = exobiology.estimate_confirmed_value(genus, species)
    if confirmed_value is not None:
        fields["confirmed_value"] = confirmed_value
    store.update_species_progress(progress_id, **fields)

    if not _too_close_to_existing_sample(state, genus, latitude, longitude):
        state.sample_positions.setdefault(genus, []).append((latitude, longitude, color_name))
    return {"panel": True, "overlay": "radar"}

def on_sell_organic_data(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    """ BioData doesn't reliably itemize what actually got sold for how much (e.g. a "sell
    all" at Vista Genomics) -- presume every completed-but-unsold sample was sold rather than
    trying to match individual BioData entries back to specific bodies. """
    if state.cmdr_id is None:
        return {}
    bio_data:list = entry.get("BioData", [])
    total:int = sum(item.get("Value", 0) + item.get("Bonus", 0) for item in bio_data)
    if total > 0:
        store.record_sale(state.cmdr_id, "exobiology", now_iso(), state.system_name or None, total, json.dumps(entry))

    store.mark_all_completed_species_sold(state.cmdr_id)
    return {"panel": True}
