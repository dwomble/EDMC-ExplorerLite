"""
Unit tests for handlers_bodies.on_scan()'s belt-cluster exclusion. Pure store + handler calls,
no journal/Tk harness needed.

Run with:
    .venv/bin/python -m pytest tests/test_belt_cluster_scan.py -v --tb=short
"""
import pytest
from typing import Generator

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_bodies

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

BELT_CLUSTER_SCAN:dict = {
    "event": "Scan", "ScanType": "AutoScan", "BodyName": "Deltius A Belt Cluster 1", "BodyID": 5,
    # Confirmed against a real captured journal log: neither StarType nor PlanetClass at all.
}

class TestOnScanBeltCluster:

    def test_belt_cluster_scan_creates_no_body_row(self, store:ExplorerStore) -> None:
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "Deltius")

        handlers_bodies.on_scan(store, state, BELT_CLUSTER_SCAN)

        assert store.get_bodies_for_system(state.system_id) == []

    def test_belt_cluster_scans_do_not_inflate_the_scanned_body_count(self, store:ExplorerStore) -> None:
        """
        Real-world regression: "N of M scanned" read something like "20 of 9 scanned" -- more
        scanned than the honk itself ever reported. A belt cluster's Scan event was being
        treated as a real "Planet" body and stamped scanned_at, inflating the count well past
        honk_body_count (which excludes belt clusters -- that's what NonBodyCount is for).
        """
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")
        state.system_id = store.get_or_create_system(state.cmdr_id, 1, "Deltius")

        real_planet:dict = {
            "event": "Scan", "ScanType": "Detailed", "BodyName": "Deltius A 1", "BodyID": 1,
            "PlanetClass": "Rocky body", "AtmosphereType": "None", "Volcanism": "",
            "SurfaceTemperature": 200.0, "SurfaceGravity": 5.0, "TerraformState": "",
        }
        handlers_bodies.on_scan(store, state, real_planet)
        for belt_body_id in (2, 3, 4, 5, 6):
            handlers_bodies.on_scan(store, state, {**BELT_CLUSTER_SCAN, "BodyID": belt_body_id})

        assert store.count_scanned_bodies_for_system(state.system_id) == 1

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
