"""
Unit tests for the "which body's exobiology list is shown" fallback: the current
body while we're at one, else the last body DSSed with confirmed biology. Pure
store + handler calls, no journal/Tk harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_bio_focus_body.py -v --tb=short
"""
import pytest
from typing import Generator

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_bodies, handlers_context

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

class TestExobioFocusBodyId:

    def test_prefers_the_current_body_over_the_last_dssed_one(self) -> None:
        s = ExplorerState()
        s.body_id, s.last_bio_body_id = 1, 2
        assert s.exobio_focus_body_id == 1

    def test_falls_back_to_the_last_dssed_body(self) -> None:
        s = ExplorerState()
        s.body_id, s.last_bio_body_id = None, 2
        assert s.exobio_focus_body_id == 2

    def test_none_when_neither_is_known(self) -> None:
        assert ExplorerState().exobio_focus_body_id is None

class TestOnSaaSignalsFoundSetsLastBioBody:

    def test_records_the_body_when_genuses_are_found(self, store:ExplorerStore, state:ExplorerState) -> None:
        handlers_bodies.on_saa_signals_found(store, state, {
            "BodyID": 1, "BodyName": "Deltius 1", "Genuses": [{"Genus_Localised": "Bacterium"}],
        })
        assert state.last_bio_body_id == 1
        assert state.last_bio_body_name == "Deltius 1"

    def test_leaves_it_unset_when_no_genuses_are_found(self, store:ExplorerStore, state:ExplorerState) -> None:
        handlers_bodies.on_saa_signals_found(store, state, {"BodyID": 1, "BodyName": "Deltius 1", "Genuses": []})
        assert state.last_bio_body_id is None

class TestEnterSystemClearsLastBioBody:

    def test_a_system_jump_drops_the_previous_systems_bio_body(self, store:ExplorerStore, state:ExplorerState) -> None:
        """ Its body_id is only meaningful paired with the system it was DSSed in --
        carrying it into a new system risks colliding with an unrelated body there. """
        state.last_bio_body_id = 1
        state.last_bio_body_name = "Deltius 1"
        handlers_context.enter_system(store, state, {"SystemAddress": 2, "SystemName": "Nextius"})
        assert state.last_bio_body_id is None
        assert state.last_bio_body_name == ""

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
