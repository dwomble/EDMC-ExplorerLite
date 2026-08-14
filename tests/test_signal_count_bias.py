"""
Unit tests for the signal-count chain bias (explorer/valuation/signal_count_bias.py). Pure
functions, no DB/journal/Tk involved -- doesn't need the harness.

Run with:
    .venv/bin/python -m pytest tests/test_signal_count_bias.py -v --tb=short
"""
import pytest

from explorer.valuation.signal_count_bias import expected_genera_for_signal_count, preferred_species_for_tier

class TestExpectedGeneraForSignalCount:

    def test_tier_1_defaults_to_bacterium(self) -> None:
        assert expected_genera_for_signal_count(1, "CarbonDioxide", "Rocky body", False) == {"Bacterium"}

    def test_tier_1_hmc_exception_prefers_stratum_when_candidate_present(self) -> None:
        result = expected_genera_for_signal_count(1, "CarbonDioxide", "High metal content body", True)
        assert result == {"Stratum"}

    def test_tier_1_hmc_without_stratum_candidate_still_falls_back_to_bacterium(self) -> None:
        # HMC alone isn't enough -- Stratum Tectonicas must actually be an eligible candidate
        # (never override eligibility genus_prediction.py didn't already grant).
        result = expected_genera_for_signal_count(1, "CarbonDioxide", "High metal content body", False)
        assert result == {"Bacterium"}

    def test_cumulative_tiers_build_up(self) -> None:
        assert expected_genera_for_signal_count(3, "CarbonDioxide", "Rocky body", False) == {"Bacterium", "Stratum", "Tussock"}
        assert expected_genera_for_signal_count(4, "CarbonDioxide", "Rocky body", False) == {
            "Bacterium", "Stratum", "Tussock", "Osseus", "Tubus",
        }
        assert expected_genera_for_signal_count(5, "CarbonDioxide", "Rocky body", False) == {
            "Bacterium", "Stratum", "Tussock", "Osseus", "Tubus", "Concha", "Frutexa",
        }

    def test_exception_atmospheres_disable_the_whole_chain(self) -> None:
        for atmosphere in ("Water", "Oxygen", "Nitrogen"):
            assert expected_genera_for_signal_count(2, atmosphere, "Rocky body", False) is None

    def test_signal_count_above_five_breaks_open_no_bias(self) -> None:
        assert expected_genera_for_signal_count(6, "CarbonDioxide", "Rocky body", False) is None

    def test_zero_or_negative_signal_count_has_no_bias(self) -> None:
        assert expected_genera_for_signal_count(0, "CarbonDioxide", "Rocky body", False) is None

class TestPreferredSpeciesForTier:

    def test_stratum_bias_at_tier_two(self) -> None:
        assert preferred_species_for_tier("Stratum", 2) == ["Stratum Paleas", "Stratum Laminamus"]

    def test_tussock_bias_at_tier_three(self) -> None:
        assert preferred_species_for_tier("Tussock", 3) == ["Tussock Pennatis", "Tussock Capillum"]

    def test_no_bias_for_a_genus_outside_its_own_tier(self) -> None:
        assert preferred_species_for_tier("Stratum", 3) == []

    def test_no_bias_when_signal_count_unknown(self) -> None:
        assert preferred_species_for_tier("Tussock", None) == []

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
