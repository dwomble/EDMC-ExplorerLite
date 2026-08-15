"""
Unit tests for the first-discovery/first-mapped/first-logged bonus helpers in cartography.py
and exobiology.py. Pure functions, no store/harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_first_discovery_bonus.py -v --tb=short
"""
import pytest

from explorer.valuation import cartography, exobiology, exobiology_data

class TestScanValueWithBonus:

    def test_adds_the_bonus_when_not_yet_discovered(self) -> None:
        assert cartography.scan_value_with_bonus(500_000, was_discovered=False) == 800_000

    def test_no_bonus_once_already_discovered(self) -> None:
        assert cartography.scan_value_with_bonus(500_000, was_discovered=True) == 500_000

class TestMappingValueForEligibility:

    def test_keeps_the_assumed_bonus_when_not_yet_mapped(self) -> None:
        """ estimate_mapping_value()'s own number already assumes first-mapped-by-us. """
        assert cartography.mapping_value_for_eligibility(370_000, was_mapped=False) == 370_000

    def test_backs_out_the_assumed_bonus_once_already_mapped(self) -> None:
        assert cartography.mapping_value_for_eligibility(160_000, was_mapped=True) == round(160_000 / 1.6)

class TestWithFirstLoggedBonus:

    def test_applies_the_5x_multiplier_when_not_yet_footfalled(self) -> None:
        assert exobiology.with_first_logged_bonus(1_000_000, was_footfalled=False) == 5_000_000
        assert exobiology_data.FIRST_LOGGED_BONUS_MULTIPLIER == 5 # the constant this helper relies on

    def test_no_bonus_once_already_footfalled(self) -> None:
        assert exobiology.with_first_logged_bonus(1_000_000, was_footfalled=True) == 1_000_000

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
