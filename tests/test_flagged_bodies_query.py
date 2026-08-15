"""
Unit tests for store.get_flagged_bodies_for_system(). Pure store calls, no journal/Tk harness
needed.

Run with:
    .venv/bin/python -m pytest tests/test_flagged_bodies_query.py -v --tb=short
"""
import pytest
from typing import Generator

from explorer.db.store import ExplorerStore

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

class TestGetFlaggedBodiesForSystem:

    def test_cartography_flagged_body_shows_even_with_no_biological_signals(self, store:ExplorerStore) -> None:
        """
        Real-world regression: FSSBodySignals fired for this body with a geological (not
        biological) signal, setting has_biological_signals=0. The outer `has_biological_signals
        IS NOT 0` guard used to apply to the WHOLE row, not just the genus-prediction branch --
        so a body flagged purely for its cartography (mapping) value vanished from the list
        entirely the moment ground truth confirmed no biology, even though flagged_value=1 had
        nothing to do with biology at all. A Terraformable HMC and Water World both scanned this
        way in one real system; the HMC (has_biological_signals=0, geological-only) disappeared
        while the Water World (has_biological_signals still NULL, no FSSBodySignals at all) stayed.
        """
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Dryoea Flyuae KL-P d5-2027")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 3, "Dryoea Flyuae KL-P d5-2027 3")
        store.update_body(body_pk, flagged_value=1, has_biological_signals=0)

        flagged = store.get_flagged_bodies_for_system(system_id)
        assert any(b["body_name"] == "Dryoea Flyuae KL-P d5-2027 3" for b in flagged), flagged

    def test_stale_prediction_still_hidden_once_biology_confirmed_absent(self, store:ExplorerStore) -> None:
        """ The narrowed guard's actual purpose: a genus_predictions row from before Scan
        shouldn't keep a body listed once FSSBodySignals says there's no biology here at all --
        unlike flagged_value, this branch has nothing else to justify showing it. """
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "QuietSpace")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "QuietSpace A 1")
        store.update_body(body_pk, has_biological_signals=0)
        store.replace_genus_predictions(body_pk, [("Bacterium", "Bacterium Aurasus", 0.9)])

        flagged = store.get_flagged_bodies_for_system(system_id)
        assert not any(b["body_name"] == "QuietSpace A 1" for b in flagged), flagged

    def test_prediction_still_shows_while_biology_status_unknown(self, store:ExplorerStore) -> None:
        """ has_biological_signals still NULL (FSSBodySignals hasn't fired for this body yet) --
        the pre-Scan genus guess is still the best information available, so it should show. """
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "QuietSpace")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "QuietSpace A 1")
        store.replace_genus_predictions(body_pk, [("Bacterium", "Bacterium Aurasus", 0.9)])

        flagged = store.get_flagged_bodies_for_system(system_id)
        assert any(b["body_name"] == "QuietSpace A 1" for b in flagged), flagged

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
