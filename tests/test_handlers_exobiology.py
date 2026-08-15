"""
Unit tests for handlers_exobiology.on_sell_organic_data's "presume all sold" behavior. Pure
store + handler calls, no journal/Tk harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_handlers_exobiology.py -v --tb=short
"""
import pytest
from typing import Generator

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_exobiology

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

def _completed_progress(store:ExplorerStore, cmdr_id:int, system_id:int, body_id:int, body_name:str, genus:str, species:str, confirmed_value:int) -> int:
    body_pk:int = store.get_or_create_body(cmdr_id, system_id, body_id, body_name)
    progress_id:int = store.get_or_create_species_progress(body_pk, genus)
    store.update_species_progress(
        progress_id, species=species, samples_taken=3, completed_at="2026-01-01T00:00:00Z", confirmed_value=confirmed_value
    )
    return progress_id

class TestOnSellOrganicData:

    def test_presumes_every_completed_unsold_row_sold_regardless_of_biodata_matching(self, store:ExplorerStore) -> None:
        """
        Real-world regression: a "sell all" at Vista Genomics fires one SellOrganicData with
        several itemized BioData entries (modeled on a real captured journal line), but
        matching each item back to the specific body/sample that earned it is unreliable --
        ambiguous the moment the same species was sampled on two different bodies (p1/p3 below).
        Presume everything completed-and-unsold got sold instead of leaving some stuck "unsold".
        """
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "Deltius")
        state.system_name = "Deltius"

        p1 = _completed_progress(store, state.cmdr_id, state.system_id, 1, "Deltius 1", "Bacterium", "Bacterium Alcyoneum", 1_658_500)
        p2 = _completed_progress(store, state.cmdr_id, state.system_id, 2, "Deltius 2", "Tussock", "Tussock Stigmasis", 19_010_800)
        p3 = _completed_progress(store, state.cmdr_id, state.system_id, 3, "Deltius 3", "Bacterium", "Bacterium Alcyoneum", 1_658_500)

        entry:dict = {
            "event": "SellOrganicData", "MarketID": 1,
            "BioData": [
                {"Genus_Localised": "Bacterium", "Species_Localised": "Bacterium Alcyoneum", "Value": 1658500, "Bonus": 0},
                {"Genus_Localised": "Tussock", "Species_Localised": "Tussock Stigmasis", "Value": 19010800, "Bonus": 0},
            ],
        }
        handlers_exobiology.on_sell_organic_data(store, state, entry)

        for progress_id, expected_value in [(p1, 1_658_500), (p2, 19_010_800), (p3, 1_658_500)]:
            row = store.get_species_progress_row(progress_id)
            assert row is not None
            assert row["sold"] == 1, dict(row)
            assert row["sold_value"] == expected_value, dict(row)

    def test_does_not_touch_incomplete_rows(self, store:ExplorerStore) -> None:
        """ Only completed (analysed) samples are "data" to sell -- in-progress sampling
        shouldn't get swept up by "presume sold". """
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "Deltius")
        state.system_name = "Deltius"

        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, 1, "Deltius 1")
        incomplete_id:int = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(incomplete_id, samples_taken=1)

        handlers_exobiology.on_sell_organic_data(store, state, {"event": "SellOrganicData", "BioData": []})

        row = store.get_species_progress_row(incomplete_id)
        assert row is not None
        assert row["sold"] == 0
        assert row["completed_at"] is None
