"""
Galactic region lookup (explorer/valuation/regions.py) and its use when entering a system.

Run with:
    .venv/bin/python -m pytest tests/test_regions.py -v --tb=short
"""
import json
import pytest
from typing import Generator

import tests.edmc.requests as mock_requests
from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_context
from explorer.valuation import regions
from explorer.valuation.genus_prediction import predict_species

SPICA_BODY:dict = {"PlanetClass": "Rocky body", "AtmosphereType": "Ammonia", "Volcanism": "",
                   "SurfaceTemperature": 173.0, "SurfaceGravity": 0.1 * 9.80665}

class TestRegions:

    def test_sol_region(self, tmp_path) -> None:
        store = ExplorerStore(tmp_path / "explorer.sqlite")
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")

        handlers_context.enter_system(store, state, {"SystemAddress": 10477373803, "SystemName": "Sol", "StarPos": (0.0, 0.0, 0.0)})
        store.close()

        assert state.region_name == "Inner Orion Spur"

    def test_starpos_none(self, tmp_path) -> None:
        store = ExplorerStore(tmp_path / "explorer.sqlite")
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("Testy")

        handlers_context.enter_system(store, state, {"SystemAddress": 1, "SystemName": "Deltius", "StarPos": None})
        store.close()

        assert state.region_name is None

    def test_excluded_region_list(self) -> None:
        assert "Aleoida Spica" in dict(predict_species("Aleoida", SPICA_BODY, None, "Galactic Centre", 1))
        assert "Aleoida Spica" not in dict(predict_species("Aleoida", SPICA_BODY, None, "Inner Orion Spur", 1))

SAMPLES:dict = {"regions": ["Galactic Centre", "The Formidine Rift", "Inner Orion Spur"],
                "species": [{"s": "Bark Mounds", "regions": [0, 0.5, 0]}, {"s": "Stratum Excutitus", "regions": [1, 1, 0]},
                            {"s": "Bacterium Aurasus", "regions": [1, 1, 1]}],
                "axes": {"temperature": [20, 600, False], "gravity": [0.03, 1.1, False], "pressure": [0.0002, 50000, True]},
                "genera": {"Bark Mounds": {"count": 7, "ridge": {"temperature": [1, 0], "gravity": [0.5, 0.5], "pressure": [0, 1]}}}}

@pytest.fixture
def refresh_env(tmp_path, monkeypatch) -> Generator[None, None, None]:
    """ Mock requests, a private refreshed-file path, a stale timestamp, and the live table restored afterwards. """
    previous:bool = mock_requests.live_requests()
    mock_requests.live_requests(False)
    monkeypatch.setattr(regions, "_local_path", lambda name: tmp_path / name)
    monkeypatch.setattr(regions, "SPECIES_REGIONS", regions.SPECIES_REGIONS)
    monkeypatch.setattr(regions, "GENUS_STATS", regions.GENUS_STATS)
    regions.config.set(f"{regions.GH_PROJECT}_regions_refreshed", 0)
    yield
    mock_requests.live_requests(previous)

class TestRefresh:

    def test_refresh_replaces_limits(self, refresh_env, tmp_path) -> None:
        mock_requests.queue_response("get", mock_requests.MockResponse(json_data=SAMPLES), url=regions.SAMPLES_URL)

        regions.refresh()

        expected:dict = {"Bark Mound": {"allowed": ["Formidine Rift"]}, "Stratum Excutitus": {"excluded": ["Inner Orion Spur"]}}
        assert regions.SPECIES_REGIONS == expected
        assert json.loads((tmp_path / "species_regions.json").read_text()) == expected
        assert regions.GENUS_STATS["Bark Mound"] == {"count": 7, "temperature": [1, 0], "gravity": [0.5, 0.5], "pressure": [0, 1]}
        assert json.loads((tmp_path / "genus_stats.json").read_text()) == regions.GENUS_STATS

    def test_failed_fetch_keeps_limits(self, refresh_env, tmp_path) -> None:
        before:dict = regions.SPECIES_REGIONS
        mock_requests.queue_response("get", mock_requests.MockResponse(status_code=503), url=regions.SAMPLES_URL)

        regions.refresh()

        assert regions.SPECIES_REGIONS is before
        assert not (tmp_path / "species_regions.json").exists()
