"""
Unit tests for handlers_sales.on_died -- ship destroyed loses any held (unsold) cartography
and completed exobiology data. Pure store + handler calls, no journal/Tk harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_handlers_sales.py -v --tb=short
"""
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

        assert store.get_system(unsold_id)["lost_at"] is not None
        assert store.get_system(sold_id)["sold_at"] is not None
        assert store.get_system(sold_id)["lost_at"] is None

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

        assert store.get_species_progress_row(unsold_id)["lost_at"] is not None
        assert store.get_species_progress_row(sold_id)["lost_at"] is None # already sold, not lost
        assert store.get_species_progress_row(in_progress_id)["lost_at"] is None # not completed yet, not "data"

    def test_is_a_noop_without_a_cmdr(self, store:ExplorerStore) -> None:
        handlers_sales.on_died(store, ExplorerState(), {"event": "Died"}) # must not raise
