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

class TestRestoreLastSession:
    """ restore_last_session() runs at plugin startup, before any journal event -- unlike
    enter_system()'s cold-start check, there's no incoming event to compare against yet, so it
    just trusts the saved snapshot outright (the next real journal event corrects it if wrong,
    same as enter_system() already does for a genuine cold start). """

    def test_restores_system_and_body_from_saved_snapshot(self, store:ExplorerStore) -> None:
        session_persist.save("Testy", 123, "Deltius", 5, "Deltius 5")

        state = ExplorerState()
        handlers_context.restore_last_session(store, state)

        assert state.cmdr == "Testy"
        assert state.cmdr_id is not None and state.cmdr_id == store.get_or_create_cmdr("Testy")
        assert state.system_address == 123
        assert state.system_name == "Deltius"
        assert state.system_id == store.get_or_create_system(state.cmdr_id, 123, "Deltius")
        assert state.body_id == 5
        assert state.body_name == "Deltius 5"

    def test_is_a_noop_when_no_snapshot_exists_yet(self, store:ExplorerStore) -> None:
        state = ExplorerState()
        handlers_context.restore_last_session(store, state)
        assert state.cmdr_id is None
        assert state.system_id is None

    def test_body_survives_login_after_restart(self, store:ExplorerStore) -> None:
        """ Regression: restore_last_session() pre-populates system_id, which used to defeat
        enter_system()'s own cold-start check (state.system_id is None) once the real LoadGame +
        Location sequence arrived after logging back in -- on_load_game()'s reset_body() would
        clear the body, and enter_system() would then treat it as a normal (non-cold-start) jump
        and never resume it, since `saved` was never loaded. """
        session_persist.save("Testy", 123, "Deltius", 5, "Deltius 5")

        state = ExplorerState()
        handlers_context.restore_last_session(store, state)
        assert state.body_id == 5

        handlers_context.on_load_game(store, state, {})
        assert state.body_id is None

        handlers_context.enter_system(store, state, {"SystemAddress": 123, "SystemName": "Deltius"})

        assert state.body_id == 5
        assert state.body_name == "Deltius 5"

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
