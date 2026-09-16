"""
Unit tests for handlers_discovery.on_honk()'s star-type-tiered verdict. Pure store + handler
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

    def test_neutron_star_is_worth_it_with_more_than_one_body(self, store:ExplorerStore) -> None:
        """
        Real-world regression: a 3-body neutron star system read as "probably quiet"/"done" --
        the old crude body/non-body heuristic had no idea the arrival star itself is a neutron
        star. The star's AutoScan normally arrives before the honk (confirmed against a real
        captured journal log), so its star_type is already known here.
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

    def test_k_type_star_is_worth_it_with_more_than_one_body(self, store:ExplorerStore) -> None:
        """ F/G/K stars are top-tier -- worth it as soon as there's more than just the star. """
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "QuietSpace")
        star_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, 0, "QuietSpace", "Star")
        store.update_body(star_pk, star_type="K")

        handlers_discovery.on_honk(store, state, {"BodyCount": 3, "NonBodyCount": 0})

        system = store.get_system(state.system_id)
        assert system is not None
        assert system["honk_hint"] == "worth a full scan"

    def test_k_type_star_alone_stays_quiet(self, store:ExplorerStore) -> None:
        """ BodyCount 1 -- just the star itself, no proxy evidence of any planets. """
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "QuietSpace")
        star_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, 0, "QuietSpace", "Star")
        store.update_body(star_pk, star_type="K")

        handlers_discovery.on_honk(store, state, {"BodyCount": 1, "NonBodyCount": 0})

        system = store.get_system(state.system_id)
        assert system is not None
        assert system["honk_hint"] == "probably quiet"

    def test_m_dwarf_needs_six_bodies(self, store:ExplorerStore) -> None:
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "DwarfSpace")
        star_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, 0, "DwarfSpace", "Star")
        store.update_body(star_pk, star_type="M")

        handlers_discovery.on_honk(store, state, {"BodyCount": 5, "NonBodyCount": 0})
        system = store.get_system(state.system_id)
        assert system is not None and system["honk_hint"] == "probably quiet"

        handlers_discovery.on_honk(store, state, {"BodyCount": 6, "NonBodyCount": 0})
        system = store.get_system(state.system_id)
        assert system is not None and system["honk_hint"] == "worth a full scan"

    def test_white_dwarf_needs_three_bodies(self, store:ExplorerStore) -> None:
        """ Not F/G/K/N/H and not M/L/T/Y -- falls to the "other" tier's 3-body threshold. """
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "WhiteDwarfSpace")
        star_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, 0, "WhiteDwarfSpace", "Star")
        store.update_body(star_pk, star_type="DA")

        handlers_discovery.on_honk(store, state, {"BodyCount": 2, "NonBodyCount": 0})
        system = store.get_system(state.system_id)
        assert system is not None and system["honk_hint"] == "probably quiet"

        handlers_discovery.on_honk(store, state, {"BodyCount": 3, "NonBodyCount": 0})
        system = store.get_system(state.system_id)
        assert system is not None and system["honk_hint"] == "worth a full scan"

    def test_no_star_scanned_yet_falls_back_to_the_other_tier(self, store:ExplorerStore) -> None:
        """ Honk arrives before any Scan at all (no body rows yet) -- no star type known, so
        the heuristic defaults to the "other" tier's 3-body threshold. """
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "QuietSpace")

        handlers_discovery.on_honk(store, state, {"BodyCount": 2, "NonBodyCount": 0})

        system = store.get_system(state.system_id)
        assert system is not None
        assert system["honk_hint"] == "probably quiet"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
