"""
End-to-end acceptance test: replays a real, unbroken play session (Cmdr name obfuscated --
see tests/journal_config/real_walkthrough.json) through the full plugin (load.py +
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
    .venv/bin/python -m pytest tests/test_real_walkthrough.py -v --tb=short
"""
import sqlite3
import pytest
from typing import Generator

from harness import TestHarness, reset_plugin_modules
from explorer.state import state as explorer_state
import explorer.db.store as store_module
import explorer.session_persist as session_persist_module
from explorer.context import Context

@pytest.fixture
def plugin(harness:TestHarness, tmp_path, monkeypatch) -> Generator[TestHarness, None, None]:
    explorer_state.reset_all()

    monkeypatch.setattr(store_module, "resolve_db_path", lambda: tmp_path / "explorer.sqlite")

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

    def test_full_walkthrough(self, plugin:TestHarness) -> None:
        plugin.load_events("real_walkthrough.json")
        plugin.play_sequence("eol_prou_walkthrough", delay=0.0)

        assert Context.store is not None
        state = explorer_state
        assert state.cmdr_id is not None and state.system_id is not None

        system:sqlite3.Row|None = Context.store.get_system(state.system_id)
        assert system is not None
        assert system["name"] == "Eol Prou IT-S c4-201"
        assert system["honk_body_count"] == 23 # this system's real FSSDiscoveryScan BodyCount

        body_pk:int = Context.store.get_or_create_body(state.cmdr_id, state.system_id, 11, "Eol Prou IT-S c4-201 AB 1 a")
        body:sqlite3.Row|None = Context.store.get_body(body_pk)
        assert body is not None
        assert body["has_biological_signals"] == 1 # real FSSBodySignals confirmed it pre-DSS

        progress:list[sqlite3.Row] = Context.store.get_species_progress(body_pk)
        by_species:dict[str, sqlite3.Row] = {row["species"]: row for row in progress}
        assert set(by_species) == {"Bacterium Aurasus", "Tubus Cavas", "Tussock Propagito"}
        assert all(row["completed_at"] is not None for row in by_species.values())
        assert all(row["samples_taken"] == 3 for row in by_species.values()) # Log + Sample + Sample each

        # Real confirmed values (exobiology_data.SPECIES_VALUE), x5 first-logged bonus --
        # WasFootfalled was false on every real Scan of this body.
        assert Context.store.get_pending_exobiology_value(state.cmdr_id) == 5 * (1_000_000 + 11_873_200 + 1_000_000)

        plugin.play_sequence("sell_organic_data", delay=0.0)

        assert all(row["sold"] == 1 for row in Context.store.get_species_progress(body_pk))
        assert Context.store.get_pending_exobiology_value(state.cmdr_id) == 0 # all 3 sold, regardless of species named

        sale:sqlite3.Row = Context.store.conn.execute(
            "SELECT event_type, total_value FROM sale_events WHERE cmdr_id = ?", (state.cmdr_id,),
        ).fetchone()
        assert sale["event_type"] == "exobiology"
        assert sale["total_value"] == 57_032_400 # real ground truth for THIS transaction (Stratum Tectonicas)

class TestRealCycle:
    """ Real 2026-08-23 session: jump, honk, scan, DSS, sample, then sell both data types. """

    def _system(self, name:str) -> sqlite3.Row:
        assert Context.store is not None
        return Context.store.conn.execute("SELECT * FROM systems WHERE name = ?", (name,)).fetchone()

    def test_full_cycle(self, plugin:TestHarness) -> None:
        plugin.load_events("real_cycle.json")
        plugin.play_sequence("explore", delay=0.0)

        store = Context.store
        assert store is not None
        cmdr_id:int|None = explorer_state.cmdr_id
        assert cmdr_id is not None

        b57:sqlite3.Row = self._system("Eol Prou YI-W b17-57")
        b69:sqlite3.Row = self._system("Eol Prou YI-W b17-69")
        assert (b57["honk_body_count"], b69["honk_body_count"]) == (14, 55)

        mapped:list[sqlite3.Row] = [b for s in (b57, b69) for b in store.get_bodies(s["id"]) if b["mapped_at"]]
        assert sorted(b["body_name"] for b in mapped) == [f"Eol Prou YI-W {n}" for n in ("b17-57 B 2", "b17-57 B 3", "b17-69 D 4")]

        species:list[sqlite3.Row] = [r for b in mapped for r in store.get_species_progress(b["id"])]
        done:list[tuple] = [(r["species"], r["samples_taken"]) for r in species if r["completed_at"]]
        assert done == [("Stratum Tectonicas", 3)] * 3
        assert {r["genus"] for r in species if not r["completed_at"]} == {"Bacterium"}
        assert store.get_pending_exobiology_value(cmdr_id) == 57_032_400
        assert store.get_pending_cartography_value(cmdr_id) > 0

        plugin.play_sequence("sell_cartography", delay=0.0)
        assert self._system("Eol Prou YI-W b17-57")["sold_at"] is not None
        assert self._system("Eol Prou YI-W b17-69")["sold_at"] is None # really sold in a later session
        assert store.get_sale_totals(cmdr_id)["cartography"] == 35_533_177 + 37_567_861 + 191_063

        plugin.play_sequence("sell_organic", delay=0.0)
        assert store.get_pending_exobiology_value(cmdr_id) == 0
        assert store.get_sale_totals(cmdr_id)["exobiology"] == 57_032_400
