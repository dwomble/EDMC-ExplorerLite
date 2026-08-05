"""
Per-body handlers: FSSBodySignals (pre-DSS signal counts), Scan (body properties + cartography
value estimate), SAAScanComplete (DSS mapping done), SAASignalsFound (post-DSS exact genus).
"""
import sqlite3

from config import config # type: ignore

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.util import now_iso
from explorer.valuation import cartography, exobiology, genus_prediction
from explorer.constants import (
    CFG_SCAN_VALUE_THRESHOLD, DEFAULT_SCAN_VALUE_THRESHOLD,
    CFG_EXOBIO_VALUE_THRESHOLD, DEFAULT_EXOBIO_VALUE_THRESHOLD,
)

BIO_SIGNAL_TYPE = "$SAA_SignalType_Biological;"

def _scan_threshold() -> int:
    return config.get_int(CFG_SCAN_VALUE_THRESHOLD, default=DEFAULT_SCAN_VALUE_THRESHOLD)

def _exobio_threshold() -> int:
    return config.get_int(CFG_EXOBIO_VALUE_THRESHOLD, default=DEFAULT_EXOBIO_VALUE_THRESHOLD)

def on_fss_body_signals(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None or state.cmdr_id is None:
        return {}
    body_id:int|None = entry.get("BodyID")
    if body_id is None:
        return {}
    body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, body_id, entry.get("BodyName", ""))

    bio_count:int = 0
    for signal in entry.get("Signals", []):
        if signal.get("Type") == BIO_SIGNAL_TYPE:
            bio_count = signal.get("Count", 0)

    store.update_body(body_pk, has_biological_signals=1 if bio_count else 0, biological_signal_count=bio_count)
    return {"panel": True}

def on_scan(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None or state.cmdr_id is None:
        return {}
    body_id:int|None = entry.get("BodyID")
    if body_id is None:
        return {}

    is_star:bool = "StarType" in entry
    body_pk:int = store.get_or_create_body(
        state.cmdr_id, state.system_id, body_id, entry.get("BodyName", ""), "Star" if is_star else "Planet"
    )

    if is_star:
        state.nearest_star_type = entry.get("StarType")

    scan_value:int = cartography.estimate_scan_value(entry)
    mapping_value:int = cartography.estimate_mapping_value(entry)
    flagged:bool = max(scan_value, mapping_value) >= _scan_threshold()

    store.update_body(
        body_pk,
        star_type=entry.get("StarType"),
        planet_class=entry.get("PlanetClass"),
        distance_ls=entry.get("DistanceFromArrivalLS"),
        was_discovered=1 if entry.get("WasDiscovered") else 0,
        was_mapped=1 if entry.get("WasMapped") else 0,
        estimated_scan_value=scan_value,
        estimated_mapping_value=mapping_value,
        flagged_value=1 if flagged else 0,
        scanned_at=now_iso(),
    )

    if not is_star and entry.get("Landable"):
        store.replace_genus_predictions(body_pk, _worthwhile_predictions(entry, state.nearest_star_type))

    return {"panel": True}

def _worthwhile_predictions(entry:dict, nearest_star_type:str|None) -> list[tuple[str, float]]:
    """ Predicted genera whose value range clears the exobio threshold -- mirrors exactly how
    on_saa_signals_found() gates flagged_exobio, so "has any prediction row" alone is a
    meaningful interest signal without needing a separate bodies column. """
    threshold:int = _exobio_threshold()
    worthwhile:list[tuple[str, float]] = []
    for genus, confidence in genus_prediction.predict_genera(entry, nearest_star_type):
        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(genus)
        value_max:int|None = value_range[1] if value_range else None
        if exobiology.exceeds_threshold(value_max, threshold):
            worthwhile.append((genus, confidence))
    return worthwhile

def on_saa_scan_complete(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None or state.cmdr_id is None:
        return {}
    body_id:int|None = entry.get("BodyID")
    if body_id is None:
        return {}
    body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, body_id, entry.get("BodyName", ""))

    probes_used:int = entry.get("ProbesUsed", 0)
    efficiency_target:int = entry.get("EfficiencyTarget", 0)
    efficient:bool = probes_used <= efficiency_target

    body:sqlite3.Row|None = store.get_body(body_pk)
    scan_value:int = body["estimated_scan_value"] if body and body["estimated_scan_value"] is not None else 0
    mapping_value:int = cartography.mapping_value_from_scan_value(scan_value, mapped_efficiently=efficient)

    store.update_body(body_pk, mapped_efficiently=1 if efficient else 0, estimated_mapping_value=mapping_value, mapped_at=now_iso())
    return {"panel": True}

def on_saa_signals_found(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None or state.cmdr_id is None:
        return {}
    body_id:int|None = entry.get("BodyID")
    if body_id is None:
        return {}
    body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, body_id, entry.get("BodyName", ""))

    value_max_overall:int = 0
    for g in entry.get("Genuses", []):
        genus:str = g.get("Genus_Localised") or g.get("Genus", "")
        store.upsert_body_genus(body_pk, genus, None, "SAASignalsFound")
        store.get_or_create_species_progress(body_pk, genus)

        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(genus)
        if value_range is not None:
            value_max_overall = max(value_max_overall, value_range[1])

    flagged_exobio:bool = exobiology.exceeds_threshold(value_max_overall or None, _exobio_threshold())
    store.update_body(
        body_pk,
        estimated_exobio_value_min=0,
        estimated_exobio_value_max=value_max_overall,
        flagged_exobio=1 if flagged_exobio else 0,
    )
    return {"panel": True, "overlay": "radar"}
