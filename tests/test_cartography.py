"""
Unit tests for explorer.valuation.cartography's planet categorization.

Run with:
    .venv/bin/python -m pytest tests/test_cartography.py -v --tb=short
"""
import pytest

from explorer.valuation import cartography

class TestPlanetCategoryGasGiantCollision:

    def test_gas_giant_with_ammonia_life_is_not_bucketed_as_ammonia_world(self) -> None:
        """ Regression: this collided with "ammonia" and priced at 3.39M Cr instead of ~11k. """
        assert cartography._planet_category("Gas giant with ammonia based life") == "default"

    def test_gas_giant_with_water_based_life_is_not_bucketed_as_water_world(self) -> None:
        assert cartography._planet_category("Gas giant with water based life") == "default"

    def test_plain_ammonia_world_is_still_bucketed_as_ammonia(self) -> None:
        assert cartography._planet_category("Ammonia world") == "ammonia"

    def test_plain_water_world_is_still_bucketed_as_water_or_earthlike(self) -> None:
        assert cartography._planet_category("Water world") == "water_or_earthlike"

    def test_sudarsky_gas_giants_are_default_category(self) -> None:
        assert cartography._planet_category("Sudarsky class I gas giant") == "default"
        assert cartography._planet_category("Helium rich gas giant") == "default"
        assert cartography._planet_category("Water giant") == "default"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
