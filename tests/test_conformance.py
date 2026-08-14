"""
End-to-end conformance test for EDMC-ExplorerLite: replays a full honk -> FSS -> DSS ->
exobiology -> sell journal sequence and checks the resulting DB state.

Run with:
    .venv/bin/python -m pytest tests/test_conformance.py -v --tb=short

`harness` (session-scoped, one shared Tk root for the whole test run) comes from conftest.py
-- see its docstring for why. `plugin` here is function-scoped and cycles
plugin_start3/plugin_stop fresh per test on that shared root.
"""
import pytest
from typing import Generator

from harness import TestHarness, reset_plugin_modules

from explorer.constants import CFG_SCAN_VALUE_THRESHOLD

@pytest.fixture
def plugin(harness:TestHarness, tmp_path, monkeypatch) -> Generator[TestHarness, None, None]:
    # explorer.state.state is a module-level singleton (correct for production -- it should
    # persist across a real EDMC session) but isn't reset by reset_plugin_modules(), so it
    # must be reset explicitly here for test isolation across separate temp DBs.
    from explorer.state import state as explorer_state
    explorer_state.reset_all()

    # Redirect the DB to a per-test temp path so tests don't accumulate state across runs.
    import explorer.db.store as store_module
    monkeypatch.setattr(store_module, "resolve_db_path", lambda: tmp_path / "explorer.sqlite")

    import explorer.session_persist as session_persist_module
    monkeypatch.setattr(session_persist_module, "resolve_session_path", lambda: tmp_path / "session_state.json")

    # Low threshold so this fixture's modest test values reliably clear it, independent of
    # exact cartography-formula fidelity (which is explicitly approximate, see cartography.py).
    harness.config.set(CFG_SCAN_VALUE_THRESHOLD, 50000)

    reset_plugin_modules() # fresh `load` module state (updater/store/panel globals) per test
    from load import plugin_start3, plugin_app, plugin_stop, journal_entry, dashboard_entry
    plugin_start3(str(harness.plugin_dir))
    plugin_app(harness.parent)

    harness.journal_handlers.clear() # avoid accumulating handlers across tests on this shared harness
    harness.register_journal_handler(journal_entry, "Testy", "Deltius", False)
    harness.dashboard_handlers.clear()
    harness.register_dashboard_handler(dashboard_entry)

    yield harness

    plugin_stop()
    harness.assert_no_unhandled_exceptions()

class TestFullWalkthrough:

    def test_full_walkthrough(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        import load
        from explorer.state import state

        assert state.system_name == "Deltius"
        assert state.cmdr == "Testy"

        cmdr_id = load.store.get_or_create_cmdr("Testy")
        system_id = load.store.get_or_create_system(cmdr_id, 999000111, "Deltius")

        system = load.store.get_system(system_id)
        assert system["honk_body_count"] == 3
        assert system["honk_non_body_count"] == 2
        assert system["all_bodies_found"] == 1
        assert system["fss_body_count"] == 3
        assert system["sold_at"] is not None # MultiSellExplorationData named this system

        flagged = load.store.get_flagged_bodies_for_system(system_id)
        flagged_body_ids = {b["body_id"] for b in flagged}
        assert 1 in flagged_body_ids # Deltius A 1, metal rich -- should clear the (lowered) threshold

        body2 = load.store.get_or_create_body(cmdr_id, system_id, 2, "Deltius A 2")
        genuses = load.store.get_body_genuses(body2)
        assert len(genuses) == 1
        assert genuses[0]["genus"] == "Bacterium"

        body2_row = load.store.get_body(body2)
        assert body2_row["flagged_exobio"] == 1 # Bacterium's range tops out at 9.1M, above the 5M default threshold

        progress = load.store.get_species_progress_for_body(body2)
        assert len(progress) == 1
        assert progress[0]["genus"] == "Bacterium"
        assert progress[0]["species"] == "Bacterium Aurasus"
        assert progress[0]["samples_taken"] == 3
        assert progress[0]["completed_at"] is not None
        assert progress[0]["confirmed_value"] == 1_000_000 # Bacterium Aurasus base value
        assert progress[0]["sold"] == 1
        assert progress[0]["sold_value"] == 5_000_000

        totals = load.store.get_cmdr_totals(cmdr_id)
        assert totals["actual_cartography_credits"] == 600_000
        assert totals["actual_exobiology_credits"] == 5_000_000

    def test_honk_only_records_heuristic(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("honk_only", 0.02)

        import load
        cmdr_id = load.store.get_or_create_cmdr("Testy")
        system_id = load.store.get_or_create_system(cmdr_id, 555000222, "QuietSpace")
        system = load.store.get_system(system_id)
        assert system["honk_body_count"] == 1
        assert system["honk_hint"] == "probably quiet"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
