"""
Compact panel: plugin_app's Tk frame. Fixed <=40 char width, vertical scrollbar past 5
visible lines, collapses to a single muted line when idle.
"""
import tkinter as tk
import sqlite3
from typing import Callable

import explorer.utils.th as th


from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState

WIDTH_CHARS = 40
VISIBLE_LINES = 5
LINE_HEIGHT_PX = 18 # approximate for the default EDMC font; tune once seen in a real window

def _truncate(text:str) -> str:
    return text if len(text) <= WIDTH_CHARS else text[:WIDTH_CHARS - 1] + "…"

def _credits(value:int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M Cr"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k Cr"
    return f"{value} Cr"

class ExplorerPanel:
    """ Owns the plugin_app frame and everything in it. Call refresh() after any DB change. """

    def __init__(self, parent:tk.Widget, store:ExplorerStore, state:ExplorerState) -> None:
        self.store = store
        self.state = state
        self.on_history_open:Callable[[], None]|None = None # wired up externally by load.py

        self.frame = th.Frame(parent)
        self.scroll = th.ScrollableFrame(self.frame, max_height=VISIBLE_LINES * LINE_HEIGHT_PX)
        self.scroll.pack(fill=tk.X)
        self.history_button = th.Button(self.frame, text="History", command=self._open_history)
        self.history_button.pack(fill=tk.X)

        self.refresh()

    def _open_history(self) -> None:
        if self.on_history_open:
            self.on_history_open()

    def _line(self, text:str) -> None:
        th.Label(self.scroll.interior, text=_truncate(text), anchor="w", justify="left").pack(fill="x")

    def refresh(self) -> None:
        self.scroll.clear()

        system = self.store.get_system(self.state.system_id) if self.state.system_id is not None else None
        if system is None:
            self._line("Explorer — idle")
            return

        self._render_system_summary(system)

        if self.state.exobiology_relevant and self.state.cmdr_id is not None and self.state.system_id is not None:
            self._render_exobiology_section()

    def _render_system_summary(self, system:sqlite3.Row) -> None:
        name = system["name"]

        if system["honk_body_count"] is None:
            self._line(f"{name} — no honk yet")
            return

        if not system["all_bodies_found"]:
            self._line(f"{name} — {system['honk_body_count']} bodies, {system['honk_non_body_count']} signals")
            self._line(f"Honk: {system['honk_hint']}")
            return

        flagged = self.store.get_flagged_bodies_for_system(system["id"])
        value_flags = [b for b in flagged if b["flagged_value"]]
        exobio_flags = [b for b in flagged if b["flagged_exobio"]]

        self._line(f"{name} — {system['fss_body_count']}/{system['fss_body_count']} scanned")
        if value_flags:
            self._line(f"* {len(value_flags)} bod{'y' if len(value_flags) == 1 else 'ies'} above threshold")
        if exobio_flags:
            self._line(f"* {len(exobio_flags)} bod{'y' if len(exobio_flags) == 1 else 'ies'} exobio potential")
        if not value_flags and not exobio_flags:
            self._line("Nothing flagged yet")

        if flagged:
            self._line("-" * WIDTH_CHARS)
            for body in flagged:
                self._render_flagged_body_line(body)

    def _render_flagged_body_line(self, body:sqlite3.Row) -> None:
        tags = []
        if body["flagged_value"]:
            value = max(body["estimated_scan_value"] or 0, body["estimated_mapping_value"] or 0)
            tags.append(_credits(value))
        if body["flagged_exobio"]:
            tags.append(f"exobio~{_credits(body['estimated_exobio_value_max'] or 0)}")
        self._line(f"{body['body_id']}: {', '.join(tags)}")

    def _render_exobiology_section(self) -> None:
        assert self.state.cmdr_id is not None and self.state.system_id is not None and self.state.body_id is not None
        body_pk = self.store.get_or_create_body(self.state.cmdr_id, self.state.system_id, self.state.body_id, self.state.body_name)
        self._line(f"{self.state.body_name or 'body'} — exobiology")

        progress = self.store.get_species_progress_for_body(body_pk)
        if not progress:
            self._line("No genus detected yet")
            return
        for row in progress:
            self._render_species_line(row)

    def _render_species_line(self, row:sqlite3.Row) -> None:
        name = row["species"] or f"{row['genus']} sp."
        done = " ✓" if row["completed_at"] else ""
        self._line(f"{name} — {row['samples_taken']}/3{done}")
