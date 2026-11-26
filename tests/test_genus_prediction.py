"""
Unit tests for the pre-DSS genus predictor (explorer/valuation/genus_prediction.py) and the exobiology filter.

Run with:
    .venv/bin/python -m pytest tests/test_genus_prediction.py -v --tb=short
"""
import pytest

from explorer.constants import CFG_EXOBIO_FILTER, DEFAULT_EXOBIO_FILTER
from explorer.db.store import ExplorerStore
from explorer.journal import handlers_bodies
from explorer.journal.handlers_bodies import BIO_SIGNAL_TYPE
from explorer.state import ExplorerState
from explorer.valuation.genus_prediction import predict_genera, predict_species, presence

def _entry(planet_class:str, atmosphere:str, volcanism:str, temp_k:float, gravity_g:float) -> dict:
    return {
        "PlanetClass": planet_class,
        "AtmosphereType": atmosphere,
        "Volcanism": volcanism,
        "SurfaceTemperature": temp_k,
        "SurfaceGravity": gravity_g * 9.80665,
    }

class TestPredictGenera:

    def test_close_match_scores_near_full_confidence(self) -> None:
        # Rocky body / CarbonDioxide / no volcanism / mid-range temp+gravity for Tubus
        # (160-195.2K, max 0.1521G) -- comfortably inside on every axis. Tubus's rulesets are
        # all `unmodeled`, so this needs confirmed biology to exercise the matching itself.
        entry = _entry("Rocky body", "CarbonDioxide", "", 178.0, 0.1)
        results = dict(predict_genera(entry, None, has_biological_signals=1))
        assert "Tubus" in results
        assert results["Tubus"] >= 0.99

    def test_incompatible_body_excludes_every_genus(self) -> None:
        # No genus in the table lists Helium as a compatible atmosphere.
        entry = _entry("Icy body", "Helium", "", 1.0, 50.0)
        assert predict_genera(entry, None) == []

    def test_borderline_temperature_scores_between_zero_and_one(self) -> None:
        # Tussock has several overlapping CarbonDioxide rulesets (different species); the
        # widest cluster tops out at 197K. Push just past that shared upper edge -- gravity
        # stays comfortably inside every ruleset's range so temperature is the only tapering
        # factor -- landing in the margin instead of squarely inside or fully excluded.
        entry = _entry("Rocky body", "CarbonDioxide", "", 197.5, 0.2)
        results = dict(predict_genera(entry, None, has_biological_signals=1))
        assert "Tussock" in results
        assert 0.0 < results["Tussock"] < 1.0

    def test_hard_volcanism_gate_excludes_mismatch(self) -> None:
        # Fumerola requires volcanism present; a volcanism-free body must exclude it even
        # though every other axis (icy body, ammonia atmosphere, temp, gravity) would match.
        entry = _entry("Icy body", "Ammonia", "", 100.0, 0.1)
        results = dict(predict_genera(entry, None))
        assert "Fumerola" not in results

    def test_hard_star_type_gate_excludes_mismatch(self) -> None:
        # Anemone requires an exotic nearby star; an ordinary M dwarf must exclude it even
        # though body/atmosphere/temp/gravity would otherwise match (metal-rich, airless).
        entry = _entry("Metal rich body", "None", "Any", 1000.0, 1.0)
        results = dict(predict_genera(entry, "M"))
        assert "Anemone" not in results

    def test_results_sorted_by_confidence_descending(self) -> None:
        entry = _entry("Rocky body", "CarbonDioxide", "", 178.0, 0.1)
        results = predict_genera(entry, None)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_region_requirement_ignored_when_region_unset(self) -> None:
        # Amphora Plants have a region requirement, so check that we still
        # predict them when region is unknown
        entry = _entry("Metal rich body", "None", "metallic", 1500.0, 1.0)
        results = dict(predict_genera(entry, "A", None, 1))
        assert "Amphora Plant" in results


    def test_region_requirement_excludes_mismatch(self) -> None:
        # Amphora Plants have a region requirement, so check that they're
        # excluded when region is known and doesn't match
        entry = _entry("Metal rich body", "None", "metallic", 1500.0, 1.0)
        results_outside_region = dict(predict_genera(entry, "A", "Galactic Centre", 1))
        assert "Amphora Plant" not in results_outside_region

    def test_region_requirement_includes_match(self) -> None:
        # Amphora Plants have a region requirement, so check that they're
        # predicted in a matching region
        entry = _entry("Metal rich body", "None", "metallic", 1500.0, 1.0)
        results_in_region = dict(predict_genera(entry, "A", "Norma Expanse", 1))
        assert "Amphora Plant" in results_in_region


class TestPredictSpecies:

    def test_narrows_to_the_matching_species_within_a_genus(self) -> None:
        # Tussock Ignis's own band is 161-170K; Ventusa (155-160K) and Serrati (171-174K) don't
        # reach 165K even with the tapering margin, so they should drop out entirely while
        # Ignis -- squarely inside its own range -- stays at (near) full confidence.
        entry = _entry("Rocky body", "CarbonDioxide", "", 165.0, 0.1)
        results = dict(predict_species("Tussock", entry, None, has_biological_signals=1))
        assert results.get("Tussock Ignis", 0.0) >= 0.99
        assert "Tussock Ventusa" not in results
        assert "Tussock Serrati" not in results

    def test_empty_for_a_genus_with_no_species_level_data(self) -> None:
        # Anemone is airless-relevant -- deliberately not in SPECIES_RULESETS (see that
        # module's docstring) -- so callers must fall back to the genus-only guess for it.
        entry = _entry("Metal rich body", "None", "Any", 1000.0, 1.0)
        assert predict_species("Anemone", entry, "M") == []

    def test_results_sorted_by_confidence_descending(self) -> None:
        entry = _entry("Rocky body", "CarbonDioxide", "", 165.0, 0.1)
        results = predict_species("Tussock", entry, None)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_region_requirement_ignored_when_region_unset(self) -> None:
        # Stratum Frigus has a region requirement, so check that we still
        # predict it when region is unknown
        entry = _entry("Rocky body", "CarbonDioxide", "", 200.0, 0.5)
        results = dict(predict_species("Stratum", entry, "F", None, 1))
        assert "Stratum Frigus" in results
        assert results["Stratum Frigus"] > 0

    def test_region_requirement_excludes_mismatch(self) -> None:
        # Stratum Frigus has a region requirement, so check that it's excluded
        # when region is known and doesn't match
        entry = _entry("Rocky body", "CarbonDioxide", "", 200.0, 0.5)
        results = dict(predict_species("Stratum", entry, "F", "Galactic Centre", 1))
        assert "Stratum Frigus" not in results

    def test_region_requirement_includes_match(self) -> None:
        # Stratum Frigus has a region requirement, so check that it's predicted
        # in a matching region
        entry = _entry("Rocky body", "CarbonDioxide", "", 200.0, 0.5)
        results = dict(predict_species("Stratum", entry, "F", "Perseus Arm", 1))
        assert "Stratum Frigus" in results
        assert results["Stratum Frigus"] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

ARGON_BODY:dict = {"event": "Scan", "BodyName": "Argon 1", "BodyID": 3, "Landable": True, "PlanetClass": "Icy body",
                   "AtmosphereType": "Argon", "Volcanism": "carbon dioxide geysers volcanism", "SurfaceTemperature": 85.86,
                   "SurfaceGravity": 2.0857, "SurfacePressure": 9780.55}
CO2_BODY:dict = {"event": "Scan", "BodyName": "CO2 1", "BodyID": 3, "Landable": True, "PlanetClass": "Rocky body",
                 "AtmosphereType": "CarbonDioxide", "Volcanism": "", "SurfaceTemperature": 162.40,
                 "SurfaceGravity": 0.889, "SurfacePressure": 1552.76}

class TestExobioFilter:

    def test_presence_ranks_rare_genus_low(self) -> None:
        odds:dict = presence(ARGON_BODY, ["Bacterium", "Bark Mound", "Electricae", "Fonticulua", "Fumerola"], 2)
        assert odds["Bark Mound"] < 0.01 < odds["Electricae"] < 0.05 < odds["Fumerola"] < odds["Bacterium"] == 1.0

    @pytest.mark.parametrize("body, level, kept, hidden", [
        (ARGON_BODY, "None", {"Bacterium", "Fumerola"}, set()),
        (ARGON_BODY, "Medium", {"Bacterium", "Fumerola"}, {"Bark Mound", "Electricae"}),
        (CO2_BODY, "High", {"Bacterium", "Tussock"}, {"Stratum", "Osseus"}),
    ])
    def test_filter_hides_unlikely_genera(self, tmp_path, body:dict, level:str, kept:set, hidden:set) -> None:
        store = ExplorerStore(tmp_path / "explorer.sqlite")
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "Deltius")
        handlers_bodies.config.set(CFG_EXOBIO_FILTER, level)

        signals:dict = {"BodyID": 3, "BodyName": body["BodyName"], "Signals": [{"Type": BIO_SIGNAL_TYPE, "Count": 2}]}
        handlers_bodies.on_fss_body_signals(store, state, signals)
        handlers_bodies.on_scan(store, state, body)
        handlers_bodies.config.set(CFG_EXOBIO_FILTER, DEFAULT_EXOBIO_FILTER)
        shown:set = {r["genus"] for r in store.get_genus_predictions(store.get_bodies(state.system_id)[0]["id"])}
        store.close()

        assert kept <= shown
        assert not shown & hidden
