"""
Unit tests for handlers_exobiology.on_sell_organic_data's "presume all sold" behavior, and
on_codex_entry's waypoint-tagging. Pure store + handler calls, no journal/Tk harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_handlers_exobiology.py -v --tb=short
"""
import pytest
from typing import Generator

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_exobiology

ORGANIC_SUBCATEGORY = "$Codex_SubCategory_Organic_Structures;"

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

class TestOnCodexEntry:
    """ CodexEntry (the low-altitude composition scanner, ship or SRV) carries an exact
    Latitude/Longitude, unlike SAASignalsFound's aggregate genus+count -- useful for tagging a
    waypoint to a species spotted but not currently being sampled. """

    def _state(self, store:ExplorerStore) -> ExplorerState:
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "Deltius")
        return state

    def _entry(self, name_localised:str, body_id:int = 2, lat:float = -13.856755, lon:float = -116.384651) -> dict:
        return {
            "event": "CodexEntry", "SubCategory": ORGANIC_SUBCATEGORY, "Category": "$Codex_Category_Biology;",
            "Name_Localised": name_localised, "BodyID": body_id, "Latitude": lat, "Longitude": lon, "IsNewEntry": True,
        }

    def test_tags_a_waypoint_from_the_name_localised_color_variant(self, store:ExplorerStore) -> None:
        """ Real captured format is "<genus> <species> - <color>" -- the color suffix must be
        stripped before the species name will match SPECIES_VALUE's lookup table. """
        state = self._state(store)
        handlers_exobiology.on_codex_entry(store, state, self._entry("Tussock Propagito - Lime"))

        assert state.sample_positions["Tussock"] == [(-13.856755, -116.384651)]

    def test_creates_a_species_progress_row_even_without_prior_saa_signals_found(self, store:ExplorerStore) -> None:
        """ A low-altitude composition scan can happen before (or instead of) a DSS pass, so the
        genus must show up in the panel/radar even if SAASignalsFound never fired for it. """
        state = self._state(store)
        handlers_exobiology.on_codex_entry(store, state, self._entry("Tussock Propagito - Lime", body_id=5))

        assert state.cmdr_id is not None and state.system_id is not None
        body_pk:int = store.get_or_create_body(state.cmdr_id, state.system_id, 5, "")
        progress_id:int = store.get_or_create_species_progress(body_pk, "Tussock")
        row = store.get_species_progress_row(progress_id)
        assert row is not None
        assert row["completed_at"] is None # tagging isn't sampling -- doesn't complete it

    def test_ignores_non_organic_codex_entries(self, store:ExplorerStore) -> None:
        """ e.g. a stellar/geological codex entry -- no genus to tag, must be a safe no-op. """
        state = self._state(store)
        entry = self._entry("DAV Type Star")
        entry["SubCategory"] = "$Codex_SubCategory_Stars;"
        handlers_exobiology.on_codex_entry(store, state, entry)

        assert state.sample_positions == {}

    def test_ignores_unrecognized_species_names(self, store:ExplorerStore) -> None:
        """ A species not in our static SPECIES_VALUE table -- can't resolve a genus, so no-op
        rather than raising or tagging garbage. """
        state = self._state(store)
        handlers_exobiology.on_codex_entry(store, state, self._entry("Not A Real Species - Puce"))

        assert state.sample_positions == {}

    def test_appends_rather_than_overwrites_repeat_tags(self, store:ExplorerStore) -> None:
        """ Re-scanning (or scanning a second individual organism of the same species) should
        add another waypoint, not replace the first. """
        state = self._state(store)
        handlers_exobiology.on_codex_entry(store, state, self._entry("Tussock Propagito - Lime", lat=1.0, lon=2.0))
        handlers_exobiology.on_codex_entry(store, state, self._entry("Tussock Propagito - Lime", lat=3.0, lon=4.0))

        assert state.sample_positions["Tussock"] == [(1.0, 2.0), (3.0, 4.0)]
