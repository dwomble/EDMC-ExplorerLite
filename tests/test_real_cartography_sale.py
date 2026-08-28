"""
Acceptance/conformance test: replays a REAL MultiSellExplorationData event (captured from an
actual play session, Cmdr name obfuscated -- see tests/journal_config/real_cartography_sale.json)
against a known-starting database (tests/db/cartography_pre_sale.sqlite, itself built by
replaying that same fixture's real pre-sale Scan/FSDJump events through dispatch() once).

Directly regression-tests the two cartography bugs found and fixed from this exact real sale:
- on_sell_exploration_data() must record TotalEarnings (ground truth), not BaseValue+Bonus.
- get_pending_cartography_value() must drop to 0 once every held system is marked sold.

Run with:
    .venv/bin/python -m pytest tests/test_real_cartography_sale.py -v --tb=short
"""
import json
import sqlite3
import pytest
from pathlib import Path
from typing import Callable, Generator

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.journal import handlers_sales

@pytest.fixture
def sale_event() -> dict:
    with open(Path(__file__).parent / "journal_config" / "real_cartography_sale.json") as f:
        return json.load(f)["sale"][0]

class TestRealCartographySale:

    def test_records_total_earnings_not_base_plus_bonus(
        self, store_from_snapshot:Callable[[str], ExplorerStore], sale_event:dict,
    ) -> None:
        store:ExplorerStore = store_from_snapshot("cartography_pre_sale")
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("TestCmdr")

        handlers_sales.on_sell_exploration_data(store, state, sale_event)

        row:sqlite3.Row = store.conn.execute(
            "SELECT event_type, total_value FROM sale_events WHERE cmdr_id = ?", (state.cmdr_id,),
        ).fetchone()
        assert row["event_type"] == "cartography"
        assert row["total_value"] == sale_event["TotalEarnings"] # 32,490,683 -- not BaseValue+Bonus (36,100,731)

    def test_marks_the_seeded_system_sold(
        self, store_from_snapshot:Callable[[str], ExplorerStore], sale_event:dict,
    ) -> None:
        store:ExplorerStore = store_from_snapshot("cartography_pre_sale")
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("TestCmdr")

        handlers_sales.on_sell_exploration_data(store, state, sale_event)

        row:sqlite3.Row = store.conn.execute(
            "SELECT sold_at FROM systems WHERE cmdr_id = ? AND name = ?", (state.cmdr_id, "Voqooe UO-Z e320"),
        ).fetchone()
        assert row["sold_at"] is not None

    def test_pending_cartography_value_drops_to_zero_once_everything_is_sold(
        self, store_from_snapshot:Callable[[str], ExplorerStore], sale_event:dict,
    ) -> None:
        """ Regression: this real system's 5 real (unmapped) bodies are worth 207,989 Cr
        pre-sale -- confirms get_pending_cartography_value()'s fix (max, not sum, of scan vs.
        mapping value) against real Scan data, not just synthetic fixture numbers. """
        store:ExplorerStore = store_from_snapshot("cartography_pre_sale")
        state = ExplorerState()
        state.cmdr_id = store.get_or_create_cmdr("TestCmdr")
        assert store.get_pending_cartography_value(state.cmdr_id) == 207_989

        handlers_sales.on_sell_exploration_data(store, state, sale_event)

        assert store.get_pending_cartography_value(state.cmdr_id) == 0
