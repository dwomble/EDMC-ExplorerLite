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

# Short display abbreviations for the panel's flagged-body lines -- checked in order, first
# substring match wins, so put more specific classes (e.g. "earthlike") before generic ones.
PLANET_CLASS_ABBREVIATIONS:list[tuple[str, str]] = [
    ("earthlike", "ELW"),
    ("water world", "WW"),
    ("water giant", "WG"),
    ("ammonia world", "AW"),
    ("metal rich", "MR"),
    ("high metal content", "HMC"),
    ("rocky ice", "Rocky ice"),
    ("rocky body", "Rocky"),
    ("icy body", "Icy"),
    ("gas giant with water based life", "GG (water life)"),
    ("gas giant with ammonia based life", "GG (ammonia life)"),
    ("helium", "He GG"),
    ("gas giant", "GG"),
]

def _type_label(entry:dict, is_star:bool) -> str|None:
    """ Short abbreviation for the panel's flagged-body lines, e.g. "T HMC", "ELW". """
    if is_star:
        return None
    planet_class:str = (entry.get("PlanetClass") or "").lower()
    label:str|None = None
    for keyword, abbrev in PLANET_CLASS_ABBREVIATIONS:
        if keyword in planet_class:
            label = abbrev
            break
    if label is None:
        return None
    if entry.get("TerraformState") == "Terraformable":
        label = f"T {label}"
    return label

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
    return {"panel": True, "overlay": "radar"}

def on_scan(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None or state.cmdr_id is None:
        return {}
    body_id:int|None = entry.get("BodyID")
    if body_id is None:
        return {}

    is_star:bool = "StarType" in entry
    if not is_star and "PlanetClass" not in entry:
        return {} # a belt cluster (or similar) -- has neither field, unlike a real star/planet

    body_pk:int = store.get_or_create_body(
        state.cmdr_id, state.system_id, body_id, entry.get("BodyName", ""), "Star" if is_star else "Planet"
    )

    if is_star:
        state.nearest_star_type = entry.get("StarType")

    scan_value:int = cartography.estimate_scan_value(entry)
    mapping_value:int = cartography.estimate_mapping_value(entry)
    # Threshold check uses the bonus-inclusive value (real payout) -- the stored estimated_*
    # columns stay base-only so downstream readers apply the bonus fresh from was_discovered/
    # was_mapped/was_footfalled, rather than double-counting an already-applied bonus.
    scan_value_full:int = cartography.scan_value_with_bonus(scan_value, bool(entry.get("WasDiscovered")))
    mapping_value_full:int = cartography.mapping_value_for_eligibility(mapping_value, bool(entry.get("WasMapped")))
    flagged:bool = max(scan_value_full, mapping_value_full) >= _scan_threshold()

    store.update_body(
        body_pk,
        star_type=entry.get("StarType"),
        planet_class=entry.get("PlanetClass"),
        atmosphere_type=entry.get("AtmosphereType"),
        distance_ls=entry.get("DistanceFromArrivalLS"),
        surface_gravity=entry.get("SurfaceGravity"),
        was_discovered=1 if entry.get("WasDiscovered") else 0,
        was_mapped=1 if entry.get("WasMapped") else 0,
        was_footfalled=1 if entry.get("WasFootfalled") else 0,
        estimated_scan_value=scan_value,
        estimated_mapping_value=mapping_value,
        flagged_value=1 if flagged else 0,
        type_label=_type_label(entry, is_star),
        scanned_at=now_iso(),
    )

    if not is_star and entry.get("Landable"):
        # FSSBodySignals often arrives before Scan (Detailed) -- if it already confirmed real
        # biology here, existence isn't speculative anymore, so show the best guess regardless
        # of its predicted value rather than going silent just because that guess is low-value.
        existing:sqlite3.Row|None = store.get_body(body_pk)
        confirmed_biology:bool = bool(existing and existing["has_biological_signals"] == 1)
        store.replace_genus_predictions(
            body_pk, _worthwhile_predictions(entry, state.nearest_star_type, bypass_threshold=confirmed_biology)
        )

    return {"panel": True, "overlay": "radar"}

def _worthwhile_predictions(entry:dict, nearest_star_type:str|None, bypass_threshold:bool = False) -> list[tuple[str, str|None, float]]:
    """ Predicted (genus, species, confidence) rows whose value clears the exobio threshold,
    checked against the first-logged-bonus-inclusive value (WasFootfalled is already known at
    Scan time, same as WasDiscovered/WasMapped) -- a body only worth it WITH the bonus is still
    worth flagging. """
    threshold:int = _exobio_threshold()
    was_footfalled:bool = bool(entry.get("WasFootfalled"))
    worthwhile:list[tuple[str, str|None, float]] = []
    for genus, genus_confidence in genus_prediction.predict_genera(entry, nearest_star_type):
        species_candidates:list[tuple[str, float]] = genus_prediction.predict_species(genus, entry, nearest_star_type)
        if not species_candidates:
            value_range:tuple[int, int]|None = exobiology.estimate_genus_range(genus)
            value_max:int|None = exobiology.with_first_logged_bonus(value_range[1], was_footfalled) if value_range else None
            if bypass_threshold or exobiology.exceeds_threshold(value_max, threshold):
                worthwhile.append((genus, None, genus_confidence))
            continue

        for species, species_confidence in species_candidates:
            base_value:int|None = exobiology.estimate_confirmed_value(genus, species)
            value:int|None = exobiology.with_first_logged_bonus(base_value, was_footfalled) if base_value is not None else None
            if bypass_threshold or exobiology.exceeds_threshold(value, threshold):
                worthwhile.append((genus, species, species_confidence))

    return worthwhile

def on_saa_scan_complete(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None or state.cmdr_id is None: return {}

    body_id:int|None = entry.get("BodyID")
    if body_id is None: return {}

    body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, body_id, entry.get("BodyName", ""))

    probes_used:int = entry.get("ProbesUsed", 0)
    efficiency_target:int = entry.get("EfficiencyTarget", 0)
    efficient:bool = probes_used <= efficiency_target

    body:sqlite3.Row|None = store.get_body(body_pk)
    scan_value:int = body["estimated_scan_value"] if body and body["estimated_scan_value"] is not None else 0
    mapping_value:int = cartography.mapping_value_from_scan_value(scan_value, mapped_efficiently=efficient)

    store.update_body(body_pk, mapped_efficiently=1 if efficient else 0, estimated_mapping_value=mapping_value, mapped_at=now_iso())
    return {"panel": True, "overlay": "radar"}

def on_saa_signals_found(store:ExplorerStore, state:ExplorerState, entry:dict) -> dict:
    if state.system_id is None or state.cmdr_id is None:
        return {}
    body_id:int|None = entry.get("BodyID")
    if body_id is None:
        return {}
    body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, body_id, entry.get("BodyName", ""))

    genuses:list[dict] = entry.get("Genuses", [])
    if genuses:
        state.last_bio_body_id = body_id
        state.last_bio_body_name = entry.get("BodyName", "")

    value_max_overall:int = 0
    for g in genuses:
        genus:str = g.get("Genus_Localised") or g.get("Genus", "")
        store.upsert_body_genus(body_pk, genus, None, "SAASignalsFound")
        store.get_or_create_species_progress(body_pk, genus)

        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(genus)
        if value_range is not None:
            value_max_overall = max(value_max_overall, value_range[1])

    # Threshold check uses the bonus-inclusive value -- was_footfalled was already captured at
    # Scan time (see on_scan), same reasoning as the cartography threshold check above.
    existing_body:sqlite3.Row|None = store.get_body(body_pk)
    was_footfalled:bool = bool(existing_body and existing_body["was_footfalled"])
    value_max_full:int = exobiology.with_first_logged_bonus(value_max_overall, was_footfalled)
    flagged_exobio:bool = exobiology.exceeds_threshold(value_max_full or None, _exobio_threshold())
    store.update_body(body_pk, estimated_exobio_value_min=0, estimated_exobio_value_max=value_max_overall,
                      flagged_exobio=1 if flagged_exobio else 0)

    return {"panel": True, "overlay": "radar"}
