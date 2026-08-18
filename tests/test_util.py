"""
Unit tests for explorer/util.py's format_pending_credits() -- shared between
panel.py's header and load.py's "Clear unsold data" summary message.

Run with:
    .venv/bin/python -m pytest tests/test_util.py -v --tb=short
"""
import pytest

from explorer.util import format_pending_credits

class TestFormatPendingCredits:

    def test_zero_shows_as_a_real_zero_not_unknown(self) -> None:
        assert format_pending_credits(0) == "0 Cr"

    def test_nonzero_delegates_to_the_normal_hfplus_formatting(self) -> None:
        assert format_pending_credits(1_000_000) == "1M Cr"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
