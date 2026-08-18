"""
Unit tests for handlers_sales.on_died -- ship destroyed loses any held (unsold) cartography
and completed exobiology data. Pure store + handler calls, no journal/Tk harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_handlers_sales.py -v --tb=short
"""
import sqlite3
import pytest
from typing import Generator

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_sales

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

class TestOnDied:

    def test_marks_unsold_systems_lost_but_leaves_sold_ones_alone(self, store:ExplorerStore) -> None:
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        unsold_id:int = store.get_or_create_system(state.cmdr_id, 1, "Deltius")
        sold_id:int = store.get_or_create_system(state.cmdr_id, 2, "Speciesia")
        store.mark_system_sold(state.cmdr_id, "Speciesia", "2026-01-01T00:00:00Z")

        handlers_sales.on_died(store, state, {"event": "Died"})

        unsold:sqlite3.Row|None = store.get_system(unsold_id)
        sold:sqlite3.Row|None = store.get_system(sold_id)
        assert unsold is not None and sold is not None
        assert unsold["lost_at"] is not None
        assert sold["sold_at"] is not None
        assert sold["lost_at"] is None

    def test_marks_completed_unsold_samples_lost_but_leaves_sold_and_in_progress_alone(self, store:ExplorerStore) -> None:
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(state.cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(state.cmdr_id, system_id, 1, "Deltius 1")

        unsold_id:int = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(unsold_id, species="Bacterium Aurasus", completed_at="2026-01-01T00:00:00Z", confirmed_value=1_000_000)

        sold_id:int = store.get_or_create_species_progress(body_pk, "Tussock")
        store.update_species_progress(sold_id, species="Tussock Ignis", completed_at="2026-01-01T00:00:00Z", sold=1, sold_value=1_850_000)

        in_progress_id:int = store.get_or_create_species_progress(body_pk, "Frutexa")
        store.update_species_progress(in_progress_id, samples_taken=1)

        handlers_sales.on_died(store, state, {"event": "Died"})

        unsold:sqlite3.Row|None = store.get_species_progress_row(unsold_id)
        sold:sqlite3.Row|None = store.get_species_progress_row(sold_id)
        in_progress:sqlite3.Row|None = store.get_species_progress_row(in_progress_id)
        assert unsold is not None and sold is not None and in_progress is not None
        assert unsold["lost_at"] is not None
        assert sold["lost_at"] is None # already sold, not lost
        assert in_progress["lost_at"] is None # not completed yet, not "data"

    def test_is_a_noop_without_a_cmdr(self, store:ExplorerStore) -> None:
        handlers_sales.on_died(store, ExplorerState(), {"event": "Died"}) # must not raise

class TestMarkEverythingUnsoldLost:
    """ Shared by on_died() and the manual-clear button -- one
    definition of "everything", so they can't drift apart. """

    def test_marks_both_cartography_and_exobiology_lost(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        progress_id:int = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(progress_id, completed_at="2026-01-01T00:00:00Z", confirmed_value=1_000_000)

        handlers_sales.mark_everything_unsold_lost(store, cmdr_id, "2026-01-02T00:00:00Z")

        system:sqlite3.Row|None = store.get_system(system_id)
        progress:sqlite3.Row|None = store.get_species_progress_row(progress_id)
        assert system is not None and system["lost_at"] is not None
        assert progress is not None and progress["lost_at"] is not None
