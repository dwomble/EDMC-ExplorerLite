"""
Unit tests for handlers_discovery.on_honk()'s exotic-star override. Pure store + handler
calls, no journal/Tk harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_honk_heuristic_override.py -v --tb=short
"""
import pytest
from typing import Generator

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_discovery

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

class TestOnHonk:

    def test_neutron_star_overrides_a_quiet_verdict(self, store:ExplorerStore) -> None:
        """
        Real-world regression: a 3-body neutron star system (BodyCount below
        WORTH_IT_BODY_COUNT, NonBodyCount 0) read as "probably quiet"/"done" -- the crude
        body/non-body heuristic has no idea the arrival star itself is a neutron star. The
        star's AutoScan normally arrives before the honk (confirmed against a real captured
        journal log), so its star_type is already known here.
        """
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "Dryoea Flyuae RS-U e2-565")
        star_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, 0, "Dryoea Flyuae RS-U e2-565", "Star")
        store.update_body(star_pk, star_type="N")

        handlers_discovery.on_honk(store, state, {"BodyCount": 3, "NonBodyCount": 0})

        system = store.get_system(state.system_id)
        assert system is not None
        assert system["honk_hint"] == "worth a full scan"

    def test_ordinary_star_keeps_the_quiet_verdict(self, store:ExplorerStore) -> None:
        """ Contrast: a default-category star (e.g. K-type) with the same low counts doesn't
        get the override -- the crude heuristic's own verdict stands. """
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "QuietSpace")
        star_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, 0, "QuietSpace", "Star")
        store.update_body(star_pk, star_type="K")

        handlers_discovery.on_honk(store, state, {"BodyCount": 3, "NonBodyCount": 0})

        system = store.get_system(state.system_id)
        assert system is not None
        assert system["honk_hint"] == "probably quiet"

    def test_no_star_scanned_yet_falls_back_to_the_crude_heuristic(self, store:ExplorerStore) -> None:
        """ Honk arrives before any Scan at all (no body rows yet) -- no exotic star to check,
        stays on the crude body/non-body verdict. """
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "QuietSpace")

        handlers_discovery.on_honk(store, state, {"BodyCount": 3, "NonBodyCount": 0})

        system = store.get_system(state.system_id)
        assert system is not None
        assert system["honk_hint"] == "probably quiet"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
