"""
Session-scoped shared Tk root for the whole test run.

Creating a fresh Tk() root per test (or even per module) works fine as long as it's the
FIRST root the process creates -- but a Canvas-based widget (plugin_app builds one via
th.ScrollableFrame) created in any SUBSEQUENT root has been observed to hang `root.update()`
indefinitely on this platform/Tk build. Reproduced with a bare Canvas+Scrollbar+Label, no
plugin logic involved -- see EDMC-PluginLib's tests/test_th_scrollableframe.py for the same
finding. Sharing one root across every test file in the run (not just within one file) is
the only way to run the full `pytest tests/` sweep without hitting it.
"""
import pytest
from typing import Generator

from harness import TestHarness, reset_plugin_modules

@pytest.fixture(scope="session")
def harness() -> Generator[TestHarness, None, None]:
    TestHarness.reset_instance()
    reset_plugin_modules()
    test_harness = TestHarness()
    yield test_harness
    TestHarness.reset_instance()
