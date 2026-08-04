"""
On-body exobiology handlers: ScanOrganic (per-sample progress) and SellOrganicData (actual
credits earned, ground truth).
"""
import json

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.util import now_iso
from explorer.valuation import exobiology

# Confirmed against real captured journal lines (2026-07 sessions): every completed species
# follows exactly ScanType Log -> Sample -> Sample -> Analyse, in that order -- Log and the two
# Samples are the 3 real genetic samples; Analyse is a separate finalize/submit step seconds
# later at the same location, not a 4th sample. Only Log/Sample increment samples_taken;
# Analyse just marks completion.
SAMPLE_SCAN_TYPES = ("Log", "Sample")

def on_scan_organic(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None or state.cmdr_id is None:
        return {}
    body_id = entry.get("Body")
    if body_id is None:
        return {}
    body_name = state.body_name if state.body_id == body_id else ""
    body_pk = store.get_or_create_body(state.cmdr_id, state.system_id, body_id, body_name)

    genus = entry.get("Genus_Localised") or entry.get("Genus", "")
    species = entry.get("Species_Localised") or entry.get("Species", "")
    variant = entry.get("Variant_Localised") or entry.get("Variant", "")
    scan_type = entry.get("ScanType", "")

    progress_id = store.get_or_create_species_progress(body_pk, genus)
    row = store.get_species_progress_row(progress_id)
    now = now_iso()

    fields = dict(species=species, variant=variant, last_stage=scan_type)

    if scan_type in SAMPLE_SCAN_TYPES:
        fields["samples_taken"] = (row["samples_taken"] if row else 0) + 1
        fields["last_sample_at"] = now
        if not row or not row["first_sample_at"]:
            fields["first_sample_at"] = now

        # ScanOrganic itself carries no position -- capture the dashboard's latest lat/long as
        # this sample's position (for the overlay radar's per-sample markers, session-only,
        # see state.py). Only for real samples, not the Analyse finalize step.
        if state.has_lat_long and state.latitude is not None and state.longitude is not None:
            state.sample_positions.setdefault(genus, []).append((state.latitude, state.longitude))
    elif scan_type == "Analyse" and (not row or not row["completed_at"]):
        fields["completed_at"] = now

    confirmed_value = exobiology.estimate_confirmed_value(genus, species)
    if confirmed_value is not None:
        fields["confirmed_value"] = confirmed_value

    store.update_species_progress(progress_id, **fields)
    return {"panel": True, "overlay": "radar"}

def on_sell_organic_data(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.cmdr_id is None:
        return {}
    bio_data = entry.get("BioData", [])
    total = sum(item.get("Value", 0) + item.get("Bonus", 0) for item in bio_data)
    if total <= 0:
        return {}

    store.record_sale(state.cmdr_id, "exobiology", now_iso(), state.system_name or None, total, json.dumps(entry))

    # Best-effort attribution back to a specific body's sample row -- FIFO among this Cmdr's
    # completed, unsold rows for the same genus+species. Ambiguous if sampled on two bodies
    # before either sale; totals (above) are the ground truth regardless.
    for item in bio_data:
        genus = item.get("Genus_Localised") or item.get("Genus", "")
        species = item.get("Species_Localised") or item.get("Species", "")
        candidates = store.get_unsold_species_progress(state.cmdr_id, genus, species)
        if candidates:
            store.update_species_progress(candidates[0]["id"], sold=1, sold_value=item.get("Value", 0) + item.get("Bonus", 0))

    return {"panel": True}
