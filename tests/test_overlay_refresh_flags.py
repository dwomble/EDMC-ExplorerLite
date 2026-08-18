"""
Regression: several journal handlers changed state the overlay displays (the
flagged-body list, the Honk/FSS/DSS header, or which body is current) but only
ever returned {"panel": True} -- load.py's _apply_flags() only refreshes the
overlay when a handler's flags include "overlay", so the overlay lagged behind
the panel by up to a dashboard tick (~1s) instead of updating in the same
event. Pure store + handler calls, no journal/Tk harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_overlay_refresh_flags.py -v --tb=short
"""
import pytest
from typing import Generator

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_bodies, handlers_discovery, handlers_context

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

@pytest.fixture
def state(store:ExplorerStore) -> ExplorerState:
    s = ExplorerState()
    s.cmdr_id = store.get_or_create_cmdr("Testy")
    s.system_id = store.get_or_create_system(s.cmdr_id, 1, "Deltius")
    return s

class TestHandlersRefreshTheOverlayImmediately:

    def test_fss_body_signals(self, store:ExplorerStore, state:ExplorerState) -> None:
        result = handlers_bodies.on_fss_body_signals(store, state, {"BodyID": 1, "Signals": []})
        assert result.get("overlay")

    def test_scan(self, store:ExplorerStore, state:ExplorerState) -> None:
        result = handlers_bodies.on_scan(store, state, {"BodyID": 1, "StarType": "K"})
        assert result.get("overlay")

    def test_saa_scan_complete(self, store:ExplorerStore, state:ExplorerState) -> None:
        result = handlers_bodies.on_saa_scan_complete(store, state, {"BodyID": 1, "ProbesUsed": 3, "EfficiencyTarget": 4})
        assert result.get("overlay")

    def test_honk(self, store:ExplorerStore, state:ExplorerState) -> None:
        result = handlers_discovery.on_honk(store, state, {"BodyCount": 3, "NonBodyCount": 0})
        assert result.get("overlay")

    def test_all_bodies_found(self, store:ExplorerStore, state:ExplorerState) -> None:
        result = handlers_discovery.on_all_bodies_found(store, state, {"Count": 3})
        assert result.get("overlay")

    def test_enter_system(self, store:ExplorerStore, state:ExplorerState) -> None:
        result = handlers_context.enter_system(store, state, {"SystemAddress": 1, "SystemName": "Deltius"})
        assert result.get("overlay")

    def test_approach_body(self, store:ExplorerStore, state:ExplorerState) -> None:
        result = handlers_context.on_approach_body(store, state, {"BodyID": 1, "Body": "Deltius 1"})
        assert result.get("overlay")

    def test_supercruise_exit(self, store:ExplorerStore, state:ExplorerState) -> None:
        result = handlers_context.on_supercruise_exit(store, state, {"BodyID": 1, "Body": "Deltius 1"})
        assert result.get("overlay")

    def test_leave_body(self, store:ExplorerStore, state:ExplorerState) -> None:
        result = handlers_context.on_leave_body(store, state, {})
        assert result.get("overlay")

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
