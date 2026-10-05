"""
Unit tests for the history popup (explorer/ui/history_view.py) and store.get_history_tree().

Run with:
    .venv/bin/python -m pytest tests/test_history_view.py -v --tb=short

`harness` (session-scoped, one shared Tk root) comes from conftest.py.
"""
import pytest
from typing import Generator

from harness import TestHarness, reset_plugin_modules
from explorer.db.store import ExplorerStore
from explorer.state import state as explorer_state
from explorer.constants import CFG_SCAN_VALUE_THRESHOLD, CFG_HISTORY_UNSOLD_ONLY, CFG_HISTORY_WINDOW_GEOMETRY
import explorer.db.store as store_module
import explorer.session_persist as session_persist_module
from explorer.context import Context

@pytest.fixture
def store(tmp_path) -> Generator[ExplorerStore, None, None]:
    s = ExplorerStore(tmp_path / "explorer.sqlite")
    yield s
    s.close()

@pytest.fixture
def plugin(harness:TestHarness, tmp_path, monkeypatch) -> Generator[TestHarness, None, None]:
    explorer_state.reset_all()

    monkeypatch.setattr(store_module, "resolve_db_path", lambda: tmp_path / "explorer.sqlite")

    monkeypatch.setattr(session_persist_module, "resolve_session_path", lambda: tmp_path / "session_state.json")

    harness.config.set(CFG_SCAN_VALUE_THRESHOLD, 50000)

    reset_plugin_modules()
    from load import plugin_start3, plugin_app, plugin_stop, journal_entry
    plugin_start3(str(harness.plugin_dir))
    plugin_app(harness.parent)

    harness.journal_handlers.clear()
    harness.register_journal_handler(journal_entry, "Testy", "Deltius", False)

    yield harness

    plugin_stop()
    harness.assert_no_unhandled_exceptions()

class TestHistoryTreeQuery:

    def test_history_tree_matches_walkthrough(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        assert Context.store is not None and explorer_state.cmdr_id is not None
        tree = Context.store.get_history_tree(explorer_state.cmdr_id)

        assert len(tree) == 1
        system = tree[0]
        assert system["name"] == "Deltius"
        assert system["status"] == "sold"

        bodies = {b["name"]: b for b in system["children"]}
        assert "Deltius A 2" in bodies
        species = bodies["Deltius A 2"]["children"]
        assert len(species) == 1
        assert species[0]["name"] == "Bacterium Aurasus"
        assert species[0]["status"] == "sold"
        # exo_full is the presumed sold value (base x5 first-logged bonus, since this fixture's
        # body has no WasFootfalled -- unset defaults to "nobody has yet") -- this now matches
        # the fixture's own SellOrganicData BioData (Value 1M + Bonus 4M = 5M), where the old
        # base-only presumed value (1M) used to under-estimate it.
        assert species[0]["exo_full"] == 5_000_000
        assert species[0]["exo_base"] == 1_000_000 # base -- what counts toward ED's own progression
        # Cartography and exobiology values are tracked separately -- a species row is pure
        # exobiology, a body's cartography value doesn't leak into its exobio total or vice versa.
        assert species[0]["cart_est"] == 0
        assert species[0]["cart_actual"] == 0
        assert species[0]["date"] # first_sample_at recorded

        body = bodies["Deltius A 2"]
        assert body["cart_est"] > 0 # from its own Scan (High metal content body)
        assert body["exo_base"] == 1_000_000 # rolled up from its one confirmed species
        assert body["exo_full"] == 5_000_000
        assert body["date"] # scanned_at recorded

        assert system["cart_est"] == sum(b["cart_est"] for b in system["children"])
        assert system["exo_base"] == body["exo_base"]
        assert system["exo_full"] == body["exo_full"]
        assert system["date"] # visited_at recorded

    def test_systems_default_to_most_recently_visited_first(self, store:ExplorerStore) -> None:
        """ Reverse-date order, not insertion order -- a "history" log reads naturally with the
        most recent entry at the top. """
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        s1:int = store.get_or_create_system(cmdr_id, 1, "First")
        store.update_system(s1, visited_at="2026-01-01T00:00:00")
        s2:int = store.get_or_create_system(cmdr_id, 2, "Second")
        store.update_system(s2, visited_at="2026-06-01T00:00:00")
        s3:int = store.get_or_create_system(cmdr_id, 3, "Third")
        store.update_system(s3, visited_at="2026-03-01T00:00:00")

        tree = store.get_history_tree(cmdr_id)
        assert [system["name"] for system in tree] == ["Second", "Third", "First"]

class TestSaleTotals:
    """ get_sale_totals() -- filtered summary, unlike
    get_cmdr_totals()'s all-time total. """

    def test_sums_by_event_type(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        store.record_sale(cmdr_id, "cartography", "2026-06-01T00:00:00", "Old", 1_000_000, "{}")
        store.record_sale(cmdr_id, "exobiology", "2026-06-01T00:00:00", "Old", 500_000, "{}")

        totals:dict[str, int] = store.get_sale_totals(cmdr_id)

        assert totals == {"cartography": 1_000_000, "exobiology": 500_000}

    def test_since_excludes_older_sales(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        store.record_sale(cmdr_id, "cartography", "2026-01-01T00:00:00", "Old", 1_000_000, "{}")
        store.record_sale(cmdr_id, "cartography", "2026-06-01T00:00:00", "Recent", 200_000, "{}")

        totals:dict[str, int] = store.get_sale_totals(cmdr_id, since="2026-03-01T00:00:00")

        assert totals == {"cartography": 200_000}

class TestUnsoldOnlyAndLimits:
    """ get_history_tree()'s unsold_only/since/limit filters --
    keeps a long career's popup from growing unbounded. """

    def test_unsold_only_hides_a_fully_settled_system(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        store.update_system(system_id, sold_at="2026-01-01T00:00:00Z")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        progress_id:int = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(progress_id, sold=1, sold_value=1_000_000)

        assert store.get_history_tree(cmdr_id, unsold_only=True) == []
        assert len(store.get_history_tree(cmdr_id, unsold_only=False)) == 1

    def test_unsold_only_keeps_a_system_with_pending_cartography(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        store.update_body(body_pk, estimated_scan_value=1_000_000, was_discovered=1)

        assert len(store.get_history_tree(cmdr_id, unsold_only=True)) == 1

    def test_unsold_only_keeps_a_system_with_an_unsold_species(self, store:ExplorerStore) -> None:
        """ Cartography and exobio are independent -- either one
        still pending keeps the system listed. """
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Deltius")
        store.update_system(system_id, sold_at="2026-01-01T00:00:00Z")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Deltius 1")
        store.get_or_create_species_progress(body_pk, "Bacterium") # untouched -- not sold or lost

        assert len(store.get_history_tree(cmdr_id, unsold_only=True)) == 1

    def test_since_filters_by_visited_at(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        old_id:int = store.get_or_create_system(cmdr_id, 1, "Old")
        store.update_system(old_id, visited_at="2026-01-01T00:00:00")
        recent_id:int = store.get_or_create_system(cmdr_id, 2, "Recent")
        store.update_system(recent_id, visited_at="2026-06-01T00:00:00")

        tree = store.get_history_tree(cmdr_id, since="2026-03-01T00:00:00")

        assert [system["name"] for system in tree] == ["Recent"]

    def test_since_also_includes_a_system_sold_after_an_old_visit(self, store:ExplorerStore) -> None:
        """ A sale can land well after the visit; visited_at
        alone hides it. """
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Old")
        store.update_system(system_id, visited_at="2026-01-01T00:00:00", sold_at="2026-06-01T00:00:00")

        tree = store.get_history_tree(cmdr_id, since="2026-03-01T00:00:00")

        assert [system["name"] for system in tree] == ["Old"]

    def test_since_also_includes_a_system_with_a_recently_sold_species(self, store:ExplorerStore) -> None:
        cmdr_id:int = store.get_or_create_cmdr("Testy")
        system_id:int = store.get_or_create_system(cmdr_id, 1, "Old")
        store.update_system(system_id, visited_at="2026-01-01T00:00:00")
        body_pk:int = store.get_or_create_body(cmdr_id, system_id, 1, "Old 1")
        progress_id:int = store.get_or_create_species_progress(body_pk, "Bacterium")
        store.update_species_progress(progress_id, sold=1, sold_value=1_000_000, sold_at="2026-06-01T00:00:00")

        tree = store.get_history_tree(cmdr_id, since="2026-03-01T00:00:00")

        assert [system["name"] for system in tree] == ["Old"]

    def test_hard_limit_caps_the_systems_returned(self, store:ExplorerStore, monkeypatch) -> None:
        monkeypatch.setattr(store_module, "MAX_HISTORY_SYSTEMS", 3)

        cmdr_id:int = store.get_or_create_cmdr("Testy")
        for i in range(5):
            system_id:int = store.get_or_create_system(cmdr_id, i, f"System{i}")
            store.update_system(system_id, visited_at=f"2026-01-0{i + 1}T00:00:00")

        tree = store.get_history_tree(cmdr_id)

        assert len(tree) == 3
        assert [system["name"] for system in tree] == ["System4", "System3", "System2"] # most recent 3

class TestHistoryViewPopup:

    def test_open_populates_tree_and_summary(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        assert Context.history_view is not None
        Context.history_view.open()
        assert Context.history_view.unsold_only_var is not None
        Context.history_view.unsold_only_var.set(False) # this fixture's system is fully sold
        Context.history_view.refresh()

        assert Context.history_view.window is not None
        assert Context.history_view.window.winfo_exists()
        assert Context.history_view.summary_label is not None
        assert "Exobiology — sold: 5M Cr" in Context.history_view.summary_label["text"]

        assert Context.history_view.tree is not None
        systems = Context.history_view.tree.get_children()
        assert len(systems) == 1
        bodies = Context.history_view.tree.get_children(systems[0])
        assert len(bodies) >= 1

        # Status is title-cased for display ("Sold" not "sold").
        system_values = Context.history_view.tree.item(systems[0], "values")
        assert system_values[0] == "Sold"

        Context.history_view._on_close()

    def test_unsold_only_defaults_to_checked_and_hides_a_sold_system(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02) # this fixture's system ends up fully sold

        assert Context.history_view is not None
        Context.history_view.open()

        assert Context.history_view.unsold_only_var is not None
        assert Context.history_view.unsold_only_var.get() is True
        assert Context.history_view.tree is not None
        assert Context.history_view.tree.get_children() == ()

        Context.history_view._on_close()

    def test_toggling_unsold_only_persists_and_refreshes(self, plugin:TestHarness) -> None:

        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        assert Context.history_view is not None
        Context.history_view.open()
        assert Context.history_view.unsold_only_var is not None and Context.history_view.tree is not None

        Context.history_view.unsold_only_var.set(False)
        Context.history_view._on_filter_changed()

        assert plugin.config.get_bool(CFG_HISTORY_UNSOLD_ONLY, default=True) is False
        assert len(Context.history_view.tree.get_children()) == 1

        Context.history_view._on_close()

    def test_tree_has_a_vertical_scrollbar(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        assert Context.history_view is not None
        Context.history_view.open()
        assert Context.history_view.tree is not None

        # A Treeview manages scrolling itself -- the widget on screen is a sibling Scrollbar
        # wired to it, not a property of the tree, so check its yscrollcommand is actually set.
        assert Context.history_view.tree.cget("yscrollcommand") != ""

        Context.history_view._on_close()

    def test_date_column_sorts_without_crashing_on_a_blank_date(self, plugin:TestHarness) -> None:
        """ A body with no Scan yet has no date -- the column must still be sortable rather
        than crashing on the blank string (see COLUMNS's sort_by="name" comment). """
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        assert Context.store is not None and explorer_state.cmdr_id is not None and explorer_state.system_id is not None
        Context.store.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, 99, "Deltius A 99")

        assert Context.history_view is not None
        Context.history_view.open()
        assert Context.history_view.unsold_only_var is not None and Context.history_view.tree is not None
        Context.history_view.unsold_only_var.set(False) # need the sold rows on-screen too
        Context.history_view.refresh()

        Context.history_view.tree._sort_by_name("date", False) # must not raise despite a blank date among the rows

        Context.history_view._on_close()

    def test_close_saves_the_windows_current_geometry(self, plugin:TestHarness) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)


        assert Context.history_view is not None
        Context.history_view.open()
        assert Context.history_view.window is not None
        current_geometry:str = Context.history_view.window.geometry()
        Context.history_view._on_close()

        assert plugin.config.get_str(CFG_HISTORY_WINDOW_GEOMETRY, default="") == current_geometry

    def test_open_restores_a_previously_saved_geometry(self, plugin:TestHarness, monkeypatch) -> None:
        plugin.load_events("explorer_events.json")
        plugin.play_sequence("full_walkthrough", 0.02)

        import tkinter as tk

        plugin.config.set(CFG_HISTORY_WINDOW_GEOMETRY, "620x480+15+15")
        requested:list[str] = []
        original_geometry = tk.Toplevel.geometry

        def _spy_geometry(widget, *args, **kwargs):
            if args:
                requested.append(args[0])
            return original_geometry(widget, *args, **kwargs)

        monkeypatch.setattr(tk.Toplevel, "geometry", _spy_geometry)

        assert Context.history_view is not None
        Context.history_view.open()
        assert "620x480+15+15" in requested
        Context.history_view._on_close()

    def test_refresh_without_open_window_is_a_safe_noop(self, plugin:TestHarness) -> None:
        assert Context.history_view is not None
        Context.history_view.refresh() # never opened -- must not raise

    def test_panel_history_button_opens_the_popup(self, plugin:TestHarness) -> None:
        assert Context.panel is not None
        Context.panel._open_history()

        assert Context.history_view is not None
        assert Context.history_view.window is not None
        Context.history_view._on_close()

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
