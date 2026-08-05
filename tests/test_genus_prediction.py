"""
Unit tests for the pre-DSS genus predictor (explorer/valuation/genus_prediction.py). Pure
function, no DB/journal/Tk involved -- doesn't need the harness.

Run with:
    .venv/bin/python -m pytest tests/test_genus_prediction.py -v --tb=short
"""
import pytest

from explorer.valuation.genus_prediction import predict_genera

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
        # (160-195.2K, max 0.1521G) -- comfortably inside on every axis.
        entry = _entry("Rocky body", "CarbonDioxide", "", 178.0, 0.1)
        results = dict(predict_genera(entry, None))
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
        results = dict(predict_genera(entry, None))
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

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
