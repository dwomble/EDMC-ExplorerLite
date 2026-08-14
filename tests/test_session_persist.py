"""
Unit tests for session_persist.py and its use in handlers_context.enter_system() to resume
mid-body across an EDMC-only restart. Pure/DB-only, no journal/Tk involved -- doesn't need
the harness.

Run with:
    .venv/bin/python -m pytest tests/test_session_persist.py -v --tb=short
"""
import pytest
from typing import Generator

import explorer.session_persist as session_persist
from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_context

@pytest.fixture(autouse=True)
def session_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(session_persist, "resolve_session_path", lambda: tmp_path / "session_state.json")

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

class TestSaveLoad:

    def test_load_returns_none_when_no_file_yet(self) -> None:
        assert session_persist.load() is None

    def test_save_then_load_roundtrips(self) -> None:
        session_persist.save("Testy", 123, "Deltius", 5, "Deltius 5")
        assert session_persist.load() == {
            "cmdr": "Testy", "system_address": 123, "system_name": "Deltius", "body_id": 5, "body_name": "Deltius 5",
        }

class TestEnterSystemResume:
    """ enter_system() only checks the saved snapshot on a cold start (state.system_id still
    None -- EDMC doesn't replay journal history, so this is the first system-entry event this
    process has seen), and only resumes the saved body if it's the same Cmdr in the same
    system -- otherwise something could have happened while EDMC was closed. """

    def _cold_state(self, store:ExplorerStore, cmdr:str = "Testy") -> ExplorerState:
        state = ExplorerState()
        state.cmdr = cmdr
        state.cmdr_id = store.get_or_create_cmdr(cmdr)
        return state

    def test_resumes_body_when_same_cmdr_and_system_after_cold_start(self, store:ExplorerStore) -> None:
        prior = self._cold_state(store)
        handlers_context.enter_system(store, prior, {"SystemAddress": 123, "SystemName": "Deltius"})
        handlers_context.on_approach_body(store, prior, {"BodyID": 5, "Body": "Deltius 5"})

        resumed = self._cold_state(store)
        handlers_context.enter_system(store, resumed, {"SystemAddress": 123, "SystemName": "Deltius"})

        assert resumed.body_id == 5
        assert resumed.body_name == "Deltius 5"

    def test_does_not_resume_when_system_differs(self, store:ExplorerStore) -> None:
        prior = self._cold_state(store)
        handlers_context.enter_system(store, prior, {"SystemAddress": 123, "SystemName": "Deltius"})
        handlers_context.on_approach_body(store, prior, {"BodyID": 5, "Body": "Deltius 5"})

        resumed = self._cold_state(store)
        handlers_context.enter_system(store, resumed, {"SystemAddress": 456, "SystemName": "Otherius"})

        assert resumed.body_id is None

    def test_does_not_resume_when_cmdr_differs(self, store:ExplorerStore) -> None:
        prior = self._cold_state(store, "Testy")
        handlers_context.enter_system(store, prior, {"SystemAddress": 123, "SystemName": "Deltius"})
        handlers_context.on_approach_body(store, prior, {"BodyID": 5, "Body": "Deltius 5"})

        resumed = self._cold_state(store, "OtherCmdr")
        handlers_context.enter_system(store, resumed, {"SystemAddress": 123, "SystemName": "Deltius"})

        assert resumed.body_id is None

    def test_does_not_resume_on_a_normal_jump_within_the_same_session(self, store:ExplorerStore) -> None:
        """ Not a cold start -- system_id is already set from the first jump, so a real jump to
        a system matching the (stale) saved snapshot shouldn't resurrect an old body. """
        state = self._cold_state(store)
        handlers_context.enter_system(store, state, {"SystemAddress": 123, "SystemName": "Deltius"})
        handlers_context.on_approach_body(store, state, {"BodyID": 5, "Body": "Deltius 5"})

        handlers_context.enter_system(store, state, {"SystemAddress": 123, "SystemName": "Deltius"})

        assert state.body_id is None
