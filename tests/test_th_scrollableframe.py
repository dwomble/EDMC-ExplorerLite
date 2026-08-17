"""
Unit tests for explorer/utils/th/scrollableframe.py's dark-mode scrollbar theming.

Run with:
    .venv/bin/python -m pytest tests/test_th_scrollableframe.py -v --tb=short

`harness` (session-scoped, one shared Tk root) comes from conftest.py.
"""
import pytest

from harness import TestHarness
from explorer.utils.th.scrollableframe import ScrollableFrame

class TestScrollbarTheming:

    def test_scrollbar_is_plain_tk_not_ttk(self, harness:TestHarness) -> None:
        """ ttk.Scrollbar ignores color config on mac/Windows -- see scrollableframe.py. """
        import tkinter as tk
        frame = ScrollableFrame(harness.parent)
        assert isinstance(frame._scrollbar, tk.Scrollbar)

    def test_scrollbar_picks_up_theme_colors_once_known(self, harness:TestHarness, monkeypatch) -> None:
        import explorer.utils.th.scrollableframe as scrollableframe_module
        current:dict = {"background": "grey4", "highlight": "#ff8000"}
        monkeypatch.setattr(scrollableframe_module.theme, "current", current, raising=False)

        frame = ScrollableFrame(harness.parent)
        frame._theme_scrollbar()

        assert frame._scrollbar.cget("troughcolor") == "grey4"
        assert frame._scrollbar.cget("activebackground") == "#ff8000"

    def test_is_a_safe_noop_before_the_theme_is_known(self, harness:TestHarness, monkeypatch) -> None:
        """ Mirrors the mock harness's MockTheme, which has no `.current` at all. """
        import explorer.utils.th.scrollableframe as scrollableframe_module
        monkeypatch.delattr(scrollableframe_module.theme, "current", raising=False)

        frame = ScrollableFrame(harness.parent) # must not raise
        frame._theme_scrollbar() # must not raise

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
