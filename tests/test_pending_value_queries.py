"""
Unit tests for store.get_pending_cartography_value()/get_pending_exobiology_value() --
"currently held, not yet sold" estimated totals, distinct from the actual_*_credits ground-truth
totals from real sale events. Pure store calls, no journal/Tk harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_pending_value_queries.py -v --tb=short
"""
import pytest
from typing import Generator

from explorer.db.store import ExplorerStore

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

class TestPendingCartographyValue:

    def test_sums_estimated_value_of_bodies_in_unsold_not_lost_systems(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        b1:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        b2:int = store.get_or_create_body(cmdr_id, system_id, 2, "Deltius 2")
        # was_discovered=1 -- no first-discovered bonus. was_mapped=1 backs out the +60% first-
        # mapped bonus that estimated_mapping_value already assumes (see mapping_value_for_eligibility).
        store.update_body(b1, estimated_scan_value=500_000, estimated_mapping_value=250_000, was_discovered=1, was_mapped=1)
        store.update_body(b2, estimated_scan_value=100_000, was_discovered=1, was_mapped=1) # no mapping value -- NULL, treated as 0

        assert store.get_pending_cartography_value(cmdr_id) == 500_000 + round(250_000 / 1.6) + 100_000

    def test_excludes_bodies_in_a_sold_system(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        store.update_body(body_pk, estimated_scan_value=500_000)
        store.mark_system_sold(cmdr_id, "Deltius", "2026-01-01T00:00:00Z")

        assert store.get_pending_cartography_value(cmdr_id) == 0

    def test_excludes_bodies_in_a_lost_system(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        store.update_body(body_pk, estimated_scan_value=500_000)
        store.update_system(system_id, lost_at="2026-01-01T00:00:00Z")

        assert store.get_pending_cartography_value(cmdr_id) == 0

    def test_zero_with_no_bodies(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        assert store.get_pending_cartography_value(cmdr_id) == 0

    def test_applies_first_discovered_and_first_mapped_bonuses(self, store:ExplorerStore) -> None:
        """ was_discovered/was_mapped=0 (nobody has yet) -- scan value gets +60%, and mapping
        value keeps FIRST_MAPPED_MULTIPLIER's already-assumed +60% rather than losing it. """
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        store.update_body(body_pk, estimated_scan_value=500_000, estimated_mapping_value=250_000, was_discovered=0, was_mapped=0)

        assert store.get_pending_cartography_value(cmdr_id) == 500_000 * 1.6 + 250_000

    def test_removes_first_mapped_bonus_once_someone_else_has_mapped_it(self, store:ExplorerStore) -> None:
        """ was_mapped=1 -- back out FIRST_MAPPED_MULTIPLIER's assumed +60%, since that bonus no
        longer applies. """
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        store.update_body(body_pk, estimated_scan_value=500_000, estimated_mapping_value=250_000, was_discovered=1, was_mapped=1)

        assert store.get_pending_cartography_value(cmdr_id) == 500_000 + round(250_000 / 1.6)

class TestPendingExobiologyValue:

    def test_sums_confirmed_value_of_completed_unsold_not_lost_samples(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        store.update_body(body_pk, was_footfalled=1) # no first-logged bonus -- sum stays base values only

        p1:int = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(p1, completed_at="2026-01-01T00:00:00Z", confirmed_value=1_000_000)
        p2:int = store.get_or_create_species_progress(body_pk, "Tussock")
        store.update_species_progress(p2, completed_at="2026-01-01T00:00:00Z", confirmed_value=1_850_000)

        assert store.get_pending_exobiology_value(cmdr_id) == 2_850_000

    def test_excludes_sold_samples(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")

        progress_id:int = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(progress_id, completed_at="2026-01-01T00:00:00Z", confirmed_value=1_000_000, sold=1, sold_value=1_000_000)

        assert store.get_pending_exobiology_value(cmdr_id) == 0

    def test_excludes_lost_samples(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")

        progress_id:int = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(progress_id, completed_at="2026-01-01T00:00:00Z", confirmed_value=1_000_000, lost_at="2026-01-01T00:00:00Z")

        assert store.get_pending_exobiology_value(cmdr_id) == 0

    def test_excludes_in_progress_samples(self, store:ExplorerStore) -> None:
        """ Not yet completed -- isn't "data" that could be sold yet. """
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")

        progress_id:int = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(progress_id, samples_taken=1)

        assert store.get_pending_exobiology_value(cmdr_id) == 0

    def test_zero_with_no_species_progress(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        assert store.get_pending_exobiology_value(cmdr_id) == 0

    def test_applies_first_logged_bonus_when_body_was_not_footfalled(self, store:ExplorerStore) -> None:
        """ was_footfalled=0 (nobody has set foot there yet) -- full 5x first-logged bonus. """
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        store.update_body(body_pk, was_footfalled=0)
        progress_id:int = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(progress_id, completed_at="2026-01-01T00:00:00Z", confirmed_value=1_000_000)

        assert store.get_pending_exobiology_value(cmdr_id) == 5_000_000

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
