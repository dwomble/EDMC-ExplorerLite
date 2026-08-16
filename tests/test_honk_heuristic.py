"""
Unit tests for explorer.valuation.honk_heuristic.assess()'s star-type tiers.

Run with:
    .venv/bin/python -m pytest tests/test_honk_heuristic.py -v --tb=short
"""
import pytest

from explorer.valuation import honk_heuristic

class TestAssess:

    def test_zero_bodies_is_no_bodies(self) -> None:
        assert honk_heuristic.assess(0, ["G"]) == "no bodies"

    @pytest.mark.parametrize("star_type", ["F", "G", "K", "N", "H", "SupermassiveBlackHole"])
    def test_top_tier_worth_it_with_more_than_one_body(self, star_type:str) -> None:
        assert honk_heuristic.assess(2, [star_type]) == "worth a full scan"

    @pytest.mark.parametrize("star_type", ["F", "G", "K", "N", "H"])
    def test_top_tier_quiet_with_only_the_star_itself(self, star_type:str) -> None:
        assert honk_heuristic.assess(1, [star_type]) == "probably quiet"

    @pytest.mark.parametrize("star_type", ["M", "L", "T", "Y"])
    def test_dwarf_tier_needs_six_bodies(self, star_type:str) -> None:
        assert honk_heuristic.assess(5, [star_type]) == "probably quiet"
        assert honk_heuristic.assess(6, [star_type]) == "worth a full scan"

    @pytest.mark.parametrize("star_type", ["A", "B", "O", "DA", "W", ""])
    def test_other_tier_needs_three_bodies(self, star_type:str) -> None:
        assert honk_heuristic.assess(2, [star_type]) == "probably quiet"
        assert honk_heuristic.assess(3, [star_type]) == "worth a full scan"

    def test_no_known_star_defaults_to_other_tier(self) -> None:
        assert honk_heuristic.assess(2, []) == "probably quiet"
        assert honk_heuristic.assess(3, []) == "worth a full scan"

    def test_best_tier_wins_across_multiple_stars(self) -> None:
        """ A binary system with an M dwarf companion should still get the G star's easier bar. """
        assert honk_heuristic.assess(2, ["M", "G"]) == "worth a full scan"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
