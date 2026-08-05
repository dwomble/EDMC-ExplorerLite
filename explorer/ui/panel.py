"""
Compact panel: plugin_app's Tk frame. Fixed <=60 char width, vertical scrollbar past 5
visible lines, collapses to a single muted line when idle.
"""
import tkinter as tk
import sqlite3
from typing import Callable

import explorer.utils.th as th

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.valuation import exobiology

WIDTH_CHARS:int = 60
VISIBLE_LINES:int = 5
LINE_HEIGHT_PX:int = 18 # approximate for the default EDMC font; tune once seen in a real window
MAX_PREDICTED_SHOWN:int = 3 # top-N predicted (unconfirmed) genus candidates per body

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
        self.store:ExplorerStore = store
        self.state:ExplorerState = state
        self.on_history_open:Callable[[], None]|None = None # wired up externally by load.py

        self.frame:th.Frame = th.Frame(parent)
        self.frame.columnconfigure(0, weight=1)

        # grid, not pack: th.Base (Button, Checkbutton, ...) only dedupes its light/dark
        # widget pair in its overridden .grid() -- .pack() falls through to the generic
        # proxy, which calls pack() on BOTH widgets, so the button was rendering twice.
        self.scroll:th.ScrollableFrame = th.ScrollableFrame(self.frame, max_height=VISIBLE_LINES * LINE_HEIGHT_PX)
        self.scroll.grid(row=0, column=0, sticky=tk.EW)
        self.history_button:th.Button = th.Button(self.frame, text="History", command=self._open_history)
        self.history_button.grid(row=1, column=0, sticky=tk.EW)

        self.refresh()

    def _open_history(self) -> None:
        if self.on_history_open:
            self.on_history_open()

    def _line(self, text:str) -> None:
        th.Label(self.scroll.interior, text=_truncate(text), anchor="w", justify="left").pack(fill=tk.X)

    def refresh(self) -> None:
        self.scroll.clear()

        system:sqlite3.Row|None = self.store.get_system(self.state.system_id) if self.state.system_id is not None else None
        if system is None:
            self._line("Explorer — idle")
            return

        self._render_system_summary(system)

        if self.state.exobiology_relevant and self.state.cmdr_id is not None and self.state.system_id is not None:
            self._render_exobiology_section()

    def _render_system_summary(self, system:sqlite3.Row) -> None:
        name:str = system["name"]

        if system["honk_body_count"] is None:
            self._line(f"{name} — no honk yet")
            return

        # Flagged bodies (value/exobio) are shown as soon as each is individually scanned --
        # not gated behind a full-system FSS sweep, since many explorers scan promising bodies
        # directly rather than sweeping every body in the system map first.
        if system["all_bodies_found"]:
            self._line(f"{name} — {system['fss_body_count']} bodies scanned")
        else:
            self._line(f"{name} — {system['honk_body_count']} bodies, {system['honk_non_body_count']} signals")
            self._line(f"Honk: {system['honk_hint']}")

        flagged:list[sqlite3.Row] = self.store.get_flagged_bodies_for_system(system["id"])
        value_flags:list[sqlite3.Row] = [b for b in flagged if b["flagged_value"]]
        exobio_flags:list[sqlite3.Row] = [b for b in flagged if b["flagged_exobio"]]

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
        if body["flagged_value"]:
            value:int = max(body["estimated_scan_value"] or 0, body["estimated_mapping_value"] or 0)
            self._line(f"{body['body_id']}: {_credits(value)}")
        if body["flagged_exobio"]:
            for row in self.store.get_species_progress_for_body(body["id"]):
                if row["completed_at"]: # done -- drop it, it's no longer "of interest"
                    continue
                self._line(f"{body['body_id']}: {self._exobio_progress_text(row)}")
        else:
            # No confirmed genus yet -- fall back to pre-DSS predicted candidates, if any.
            for row in self.store.get_genus_predictions_for_body(body["id"])[:MAX_PREDICTED_SHOWN]:
                self._line(f"{body['body_id']}: {self._predicted_genus_text(row)}")

    def _render_exobiology_section(self) -> None:
        assert self.state.cmdr_id is not None and self.state.system_id is not None and self.state.body_id is not None
        body_pk:int = self.store.get_or_create_body(self.state.cmdr_id, self.state.system_id, self.state.body_id, self.state.body_name)
        self._line(f"{self.state.body_name or 'body'} — exobiology")

        all_progress:list[sqlite3.Row] = self.store.get_species_progress_for_body(body_pk)
        active:list[sqlite3.Row] = [row for row in all_progress if not row["completed_at"]]
        if active:
            for row in active:
                self._line(self._exobio_progress_text(row))
            return
        if all_progress:
            self._line("All species done here")
            return

        predictions:list[sqlite3.Row] = self.store.get_genus_predictions_for_body(body_pk)[:MAX_PREDICTED_SHOWN]
        if not predictions:
            self._line("No genus detected yet")
            return
        for row in predictions:
            self._line(self._predicted_genus_text(row))

    def _predicted_genus_text(self, row:sqlite3.Row) -> str:
        """ Pre-DSS guess -- '?' and a confidence percentage mark it as unconfirmed, both of
        which disappear once SAASignalsFound confirms the real genus for this body. """
        genus:str = row["genus"]
        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(genus)
        value_max:int = value_range[1] if value_range else 0
        return f"?{genus} ~{_credits(value_max)} ({row['confidence']:.0%})"

    def _exobio_progress_text(self, row:sqlite3.Row) -> str:
        """
        Progressive detail as we learn more -- genus placeholder becomes the species name once
        confirmed (first sample), and the value estimate becomes the confirmed value at the same
        time, replacing the generic range guess rather than sitting alongside it.
        """
        genus:str = row["genus"] or "biological"
        name:str = row["species"] or f"{genus} sp."
        if row["species"]:
            return f"{name} — {row['samples_taken']}/3, {_credits(row['confirmed_value'] or 0)}"
        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(genus)
        return f"{name} ~{_credits(value_range[1] if value_range else 0)}"
