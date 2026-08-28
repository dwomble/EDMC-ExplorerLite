"""
End-to-end acceptance test: replays a real, unbroken play session (Cmdr name obfuscated --
see tests/journal_config/real_exploration_walkthrough.json) through the full plugin (load.py +
dispatch(), not just isolated store calls) -- honk, ~30 body Scans (including belt clusters and
non-landable gas giants, exercising on_scan's own exclusion logic on real data), two DSS'd
bodies, and a complete Log/Sample/Sample/Analyse cycle for all 3 genuses SAASignalsFound
predicted on one body (Bacterium, Tubus, Tussock).

The final "sell_organic_data" stage is a real SellOrganicData event too, but for an unrelated
species (Stratum Tectonicas, sold 10 real days later) -- no real sale ever named our 3 species
directly. That's the point: BioData gives species+value, never which body/sample it came from
(confirmed against every real SellOrganicData in this Cmdr's logs), so on_sell_organic_data()
never tries to match by species either -- it presumes every completed-unsold sample sold. Any
real sell event exercises that real behavior, regardless of which species it happens to name.

Run with:
    .venv/bin/python -m pytest tests/test_real_exploration_walkthrough.py -v --tb=short
"""
import sqlite3
import pytest
from typing import Generator

from harness import TestHarness, reset_plugin_modules

@pytest.fixture
def plugin(harness:TestHarness, tmp_path, monkeypatch) -> Generator[TestHarness, None, None]:
    from explorer.state import state as explorer_state
    explorer_state.reset_all()

    import explorer.db.store as store_module
    monkeypatch.setattr(store_module, "resolve_db_path", lambda: tmp_path / "explorer.sqlite")

    import explorer.session_persist as session_persist_module
    monkeypatch.setattr(session_persist_module, "resolve_session_path", lambda: tmp_path / "session_state.json")

    reset_plugin_modules()
    from load import plugin_start3, plugin_app, plugin_stop, journal_entry
    plugin_start3(str(harness.plugin_dir))
    plugin_app(harness.parent)

    harness.journal_handlers.clear()
    harness.register_journal_handler(journal_entry, "TestCmdr", "Eol Prou IT-S c4-201", False)

    yield harness

    plugin_stop()
    harness.assert_no_unhandled_exceptions()

class TestEolProuWalkthrough:

    def test_full_exploration_and_exobiology_walkthrough_including_sale(self, plugin:TestHarness) -> None:
        plugin.load_events("real_exploration_walkthrough.json")
        plugin.play_sequence("eol_prou_walkthrough", delay=0.0)

        import load
        assert load.store is not None
        state = load.explorer_state
        assert state.cmdr_id is not None and state.system_id is not None

        system:sqlite3.Row|None = load.store.get_system(state.system_id)
        assert system is not None
        assert system["name"] == "Eol Prou IT-S c4-201"
        assert system["honk_body_count"] == 23 # this system's real FSSDiscoveryScan BodyCount

        body_pk:int = load.store.get_or_create_body(state.cmdr_id, state.system_id, 11, "Eol Prou IT-S c4-201 AB 1 a")
        body:sqlite3.Row|None = load.store.get_body(body_pk)
        assert body is not None
        assert body["has_biological_signals"] == 1 # real FSSBodySignals confirmed it pre-DSS

        progress:list[sqlite3.Row] = load.store.get_species_progress_for_body(body_pk)
        by_species:dict[str, sqlite3.Row] = {row["species"]: row for row in progress}
        assert set(by_species) == {"Bacterium Aurasus", "Tubus Cavas", "Tussock Propagito"}
        assert all(row["completed_at"] is not None for row in by_species.values())
        assert all(row["samples_taken"] == 3 for row in by_species.values()) # Log + Sample + Sample each

        # Real confirmed values (exobiology_data.SPECIES_VALUE), x5 first-logged bonus --
        # WasFootfalled was false on every real Scan of this body.
        assert load.store.get_pending_exobiology_value(state.cmdr_id) == 5 * (1_000_000 + 11_873_200 + 1_000_000)

        plugin.play_sequence("sell_organic_data", delay=0.0)

        assert all(row["sold"] == 1 for row in load.store.get_species_progress_for_body(body_pk))
        assert load.store.get_pending_exobiology_value(state.cmdr_id) == 0 # all 3 sold, regardless of species named

        sale:sqlite3.Row = load.store.conn.execute(
            "SELECT event_type, total_value FROM sale_events WHERE cmdr_id = ?", (state.cmdr_id,),
        ).fetchone()
        assert sale["event_type"] == "exobiology"
        assert sale["total_value"] == 57_032_400 # real ground truth for THIS transaction (Stratum Tectonicas)
