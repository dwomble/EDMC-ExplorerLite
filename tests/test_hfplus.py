"""
Unit tests for explorer/utils/misc.py's hfplus() -- locale-aware number/date
formatting via locale.format_string(), replacing hardcoded comma/period
separators.

Run with:
    .venv/bin/python -m pytest tests/test_hfplus.py -v --tb=short
"""
import locale
import pytest
from typing import Generator

from explorer.utils.misc import hfplus

@pytest.fixture
def de_locale() -> Generator[None, None, None]:
    """ Separators follow locale, not a hardcoded value. """
    saved:str = locale.setlocale(locale.LC_ALL)
    try:
        locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
    except locale.Error:
        pytest.skip("de_DE.UTF-8 locale not installed on this machine")
    yield
    locale.setlocale(locale.LC_ALL, saved)

class TestHfplusNumbersUnderCLocale:
    """ 'C' is always available -- the deterministic, portable baseline. """

    def test_no_grouping_separator_under_c_locale(self) -> None:
        assert hfplus((1234.5, 'float', '?', '')) == "1234"

    def test_small_num_under_c_locale(self) -> None:
        assert hfplus((5.5, 'num', '?', '')) == "5.5"

    def test_small_num_caps_at_two_decimal_places(self) -> None:
        """ Regression: :n defaults to 6 sig figs (:g's default) --
        ED values never need more than 2dp. """
        assert hfplus((3.14159265358979, 'num', '?', '')) == "3.14"

    def test_small_num_rounds_rather_than_truncates(self) -> None:
        assert hfplus((9.999999, 'num', '?', '')) == "10"

    def test_abbreviated_number_under_c_locale(self) -> None:
        assert hfplus((15_000_000, 'num', '?', ' Cr')) == "15M Cr"

class TestHfplusNumbersUnderAnotherLocale:

    def test_groups_thousands_with_the_locale_separator(self, de_locale) -> None:
        assert hfplus((1234.5, 'float', '?', '')) == "1.234"

    def test_small_num_uses_the_locale_decimal_point(self, de_locale) -> None:
        assert hfplus((5.5, 'num', '?', '')) == "5,5"

    def test_abbreviated_number_uses_the_locale_decimal_point(self, de_locale) -> None:
        assert hfplus((12_345, 'num', '?', ' Cr')) == "12,3K Cr"

class TestHfplusDatetime:

    def test_drops_seconds_regardless_of_locale(self) -> None:
        assert hfplus(('2026-08-17 14:30:45', 'datetime')) == "08/17/26 14:30"

    def test_date_portion_follows_the_locale(self, de_locale) -> None:
        assert hfplus(('2026-08-17 14:30:00', 'datetime')) == "17.08.2026 14:30"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
