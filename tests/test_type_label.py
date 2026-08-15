"""
Unit tests for handlers_bodies._type_label(). Pure function, no store/harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_type_label.py -v --tb=short
"""
import pytest

from explorer.journal.handlers_bodies import _type_label

class TestTypeLabel:

    def test_terraformable_prefix_is_shortened_to_t(self) -> None:
        entry = {"PlanetClass": "High metal content body", "TerraformState": "Terraformable"}
        assert _type_label(entry, is_star=False) == "T HMC"

    def test_non_terraformable_has_no_prefix(self) -> None:
        entry = {"PlanetClass": "High metal content body", "TerraformState": ""}
        assert _type_label(entry, is_star=False) == "HMC"

    def test_stars_have_no_label(self) -> None:
        entry = {"PlanetClass": "High metal content body", "TerraformState": "Terraformable"}
        assert _type_label(entry, is_star=True) is None

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
