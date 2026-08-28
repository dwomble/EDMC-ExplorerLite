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
import shutil
import pytest
from pathlib import Path
from typing import Callable, Generator

from harness import TestHarness, reset_plugin_modules
from explorer.db.store import ExplorerStore

@pytest.fixture(scope="session")
def harness() -> Generator[TestHarness, None, None]:
    TestHarness.reset_instance()
    reset_plugin_modules()
    test_harness = TestHarness()
    yield test_harness
    TestHarness.reset_instance()

DB_DIR:Path = Path(__file__).parent / "db"

@pytest.fixture
def store_from_snapshot(tmp_path) -> Generator[Callable[[str], ExplorerStore], None, None]:
    """ store_from_snapshot("name") copies tests/db/name.sqlite (a checked-in, known-starting
    database -- empty, an old schema version, or pre-populated, whatever a test needs) to a
    private per-test working copy and opens an ExplorerStore on the copy. The checked-in
    snapshot itself is only ever read, never opened for writing, so a test can never corrupt
    it or leak state into another test. """
    opened:list[ExplorerStore] = []

    def _make(name:str) -> ExplorerStore:
        src:Path = DB_DIR / f"{name}.sqlite"
        dst:Path = tmp_path / f"{name}.sqlite"
        shutil.copy(src, dst)
        store:ExplorerStore = ExplorerStore(dst)
        opened.append(store)
        return store

    yield _make
    for store in opened:
        store.close()
