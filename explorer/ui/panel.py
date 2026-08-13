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

def _distance_str(distance_ls:float|None) -> str:
    if distance_ls is None:
        return "? ls"
    if distance_ls >= 1000:
        return f"{distance_ls / 1000:.1f}k ls"
    return f"{distance_ls:.0f} ls"

def _body_designator(system_name:str, body_name:str) -> str:
    """ The short local part of a body's name, e.g. "Deltius B 6 c" -> "B 6 c" -- system name
    is implied by context, repeating it on every line just wastes width. """
    prefix:str = system_name + " "
    if body_name.startswith(prefix):
        designator:str = body_name[len(prefix):]
        return designator if designator else body_name
    return body_name

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

        # Current body's exobiology detail: shown as soon as we have one in view (approaching
        # or dropping out of supercruise near it, well before landing) -- not gated on being
        # on-foot, so it's useful for the "should I bother landing here" decision too.
        if self.state.body_id is not None and self.state.cmdr_id is not None and self.state.system_id is not None:
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
        # FSSBodySignals already confirms biology is present on these -- not a guess, just an
        # unidentified genus pending DSS. Distinct from possible_exobio below, which is a genus
        # guessed purely from Scan conditions with no confirmed signal at all.
        known_bio:list[sqlite3.Row] = [b for b in flagged if not b["flagged_exobio"] and b["has_biological_signals"]]
        possible_exobio:list[sqlite3.Row] = [b for b in flagged if not b["flagged_exobio"] and not b["has_biological_signals"] and b["has_prediction"]]

        if value_flags:
            self._line(f"* {len(value_flags)} bod{'y' if len(value_flags) == 1 else 'ies'} above threshold")
        if exobio_flags:
            self._line(f"* {len(exobio_flags)} bod{'y' if len(exobio_flags) == 1 else 'ies'} exobio potential")
        if known_bio:
            self._line(f"* {len(known_bio)} bod{'y' if len(known_bio) == 1 else 'ies'} known biological signals")
        if possible_exobio:
            self._line(f"* {len(possible_exobio)} bod{'y' if len(possible_exobio) == 1 else 'ies'} possible exobio")
        if not flagged:
            # Once every body's confirmed, "nothing flagged" can mean "no planets at all" --
            # e.g. a binary-star-only system -- which reads as "already checked, quiet"
            # rather than a leftover "should I DSS anything here" question.
            if system["all_bodies_found"] and not self.store.system_has_any_planet(system["id"]):
                self._line("No planets — DSS not required")
            else:
                self._line("Nothing flagged yet")

        if flagged:
            self._line("-" * WIDTH_CHARS)
            for body in flagged:
                self._render_flagged_body_line(name, body)

    def _render_flagged_body_line(self, system_name:str, body:sqlite3.Row) -> None:
        """
        One line per body of interest -- name, what's interesting about it, distance, and
        total remaining value. A body drops off this list entirely once there's nothing left
        to actually do there (mapped, and any exobiology fully sampled) -- it's a to-do list,
        not a permanent record (see history for that).
        """
        tags:list[str] = []
        value:int = 0

        if body["flagged_value"] and not body["mapped_at"]:
            value += max(body["estimated_scan_value"] or 0, body["estimated_mapping_value"] or 0)
            if body["type_label"]:
                tags.append(body["type_label"])

        active:list[sqlite3.Row] = [r for r in self.store.get_species_progress_for_body(body["id"]) if not r["completed_at"]]
        if active:
            tags.append(f"{len(active)} species")
            value += sum(self._exobio_row_value(r) for r in active)
        elif not body["flagged_exobio"]:
            predictions:list[sqlite3.Row] = self.store.get_genus_predictions_for_body(body["id"])[:MAX_PREDICTED_SHOWN]
            if predictions:
                tags.append(f"{len(predictions)} species")
                value += sum(self._predicted_row_value(r) for r in predictions)
            elif body["has_biological_signals"]:
                # FSSBodySignals already confirmed biology is present here -- worth surfacing
                # even before a Scan gives us anything to guess a genus (and thus a value) from.
                tags.append("biological signals")

        if not value and not tags:
            return # nothing left to do here -- drop it

        designator:str = _body_designator(system_name, body["body_name"])
        parts:list[str] = [designator]
        if tags:
            parts.append(", ".join(tags))
        parts.append(_distance_str(body["distance_ls"]))
        parts.append(_credits(value) if value else "? Cr")
        self._line(" ".join(parts))

    def _render_exobiology_section(self) -> None:
        """
        Shown as soon as a body is in view (approach/supercruise-exit onward). Silent for a
        body with no biological interest at all, UNLESS we're actually on-foot there --
        showing "nothing here" for every uninteresting body/star/gas giant flown past would
        drown out the rest of the panel; on-foot, it's confirmation the player actually wants.
        """
        assert self.state.cmdr_id is not None and self.state.system_id is not None and self.state.body_id is not None
        body_pk:int = self.store.get_or_create_body(self.state.cmdr_id, self.state.system_id, self.state.body_id, self.state.body_name)

        all_progress:list[sqlite3.Row] = self.store.get_species_progress_for_body(body_pk)
        active:list[sqlite3.Row] = [row for row in all_progress if not row["completed_at"]]
        predictions:list[sqlite3.Row] = [] if (active or all_progress) else self.store.get_genus_predictions_for_body(body_pk)[:MAX_PREDICTED_SHOWN]

        if not active and all_progress:
            return # every genus here is fully sampled -- nothing left to do, drop the section

        if not active and not predictions and not self.state.on_foot:
            return

        self._line(f"{self.state.body_name or 'body'} — exobiology")
        if active:
            for row in active:
                self._line(self._exobio_progress_text(row))
        elif predictions:
            for row in predictions:
                self._line(self._predicted_genus_text(row))
        else:
            self._line("No genus detected yet")

    def _predicted_row_value(self, row:sqlite3.Row) -> int:
        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(row["genus"])
        return value_range[1] if value_range else 0

    def _predicted_genus_text(self, row:sqlite3.Row) -> str:
        """ Pre-DSS guess -- '?' and a confidence percentage mark it as unconfirmed, both of
        which disappear once SAASignalsFound confirms the real genus for this body. """
        return f"?{row['genus']} ~{_credits(self._predicted_row_value(row))} ({row['confidence']:.0%})"

    def _exobio_row_value(self, row:sqlite3.Row) -> int:
        if row["species"]:
            return row["confirmed_value"] or 0
        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(row["genus"] or "")
        return value_range[1] if value_range else 0

    def _exobio_progress_text(self, row:sqlite3.Row) -> str:
        """
        Progressive detail as we learn more -- genus placeholder becomes the species name once
        confirmed (first sample), and the value estimate becomes the confirmed value at the same
        time, replacing the generic range guess rather than sitting alongside it.
        """
        genus:str = row["genus"] or "biological"
        name:str = row["species"] or f"{genus} sp."
        if row["species"]:
            return f"{name} — {row['samples_taken']}/3, {_credits(self._exobio_row_value(row))}"
        return f"{name} ~{_credits(self._exobio_row_value(row))}"
