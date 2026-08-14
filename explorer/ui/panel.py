"""
Compact panel: plugin_app's Tk frame. Fixed <=60 char width, vertical scrollbar past 5
visible lines, collapses to a single muted line when idle.
"""
import tkinter as tk
import sqlite3
from typing import Callable

import explorer.utils.th as th
from explorer.utils.misc import hfplus, str_truncate

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.valuation import exobiology, signal_count_bias

WIDTH_CHARS:int = 60
VISIBLE_LINES:int = 5
LINE_HEIGHT_PX:int = 18 # approximate for the default EDMC font; tune once seen in a real window
MAX_PREDICTED_SHOWN:int = 3 # fallback cap on predicted candidates per body, only used until
# FSSBodySignals tells us the body's real biological_signal_count (see _best_predictions_for_body)
INDENT_PX:int = 14 # left offset for a table nested under its own header line (e.g. per-body biologicals)

def _credits(value:int) -> str:
    return hfplus((value, 'num', '? Cr', ' Cr'))

def _credits_range(value_min:int, value_max:int) -> str:
    """ A single exact credits string when the range has collapsed to one number (a
    species-exact value, or a genus with only one known species); otherwise a compact
    min-max range -- a genus-level guess can vary a lot by which species turns out to be
    present, and showing only the top of that range reads as a specific number it isn't. """
    if value_min >= value_max:
        return _credits(value_max)
    return f"{_credits(value_min)}-{_credits(value_max)}"

def _distance_str(distance_ls:float|None) -> str:
    return hfplus((distance_ls, 'num', '? ls', ' ls'))

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
        th.Label(self.scroll.interior, text=str_truncate(text, WIDTH_CHARS), anchor="w", justify="left").pack(fill=tk.X)

    def _render_table(self, rows:list[tuple[str, ...]], anchors:tuple[str, ...], indent:int = 0) -> None:
        """
        Grid `rows` into one Frame -- packed into the scroll as a single "line" (consistent
        with _line()) -- so Tk's grid geometry manager aligns every column to its widest cell.
        A plain space-joined string only lines up columns if the font happens to be monospace,
        which EDMC's theme doesn't guarantee.
        """
        if not rows:
            return
        table:th.Frame = th.Frame(self.scroll.interior)
        for r, row in enumerate(rows):
            last:int = len(row) - 1
            for c, (text, anchor) in enumerate(zip(row, anchors)):
                sticky:str = tk.W if anchor == "w" else tk.E
                pad:tuple[int, int] = (0, 0) if c == last else (0, 8)
                th.Label(table, text=text, anchor=anchor).grid(row=r, column=c, sticky=sticky, padx=pad)
        table.pack(fill=tk.X, padx=(indent, 0))

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
        if not flagged:
            # Once every body's confirmed, "nothing flagged" can mean "no planets at all" --
            # e.g. a binary-star-only system -- which reads as "already checked, quiet"
            # rather than a leftover "should I DSS anything here" question.
            if system["all_bodies_found"] and not self.store.system_has_any_planet(system["id"]):
                self._line("No planets — DSS not required")
            else:
                self._line("Nothing flagged yet")
        else:
            rows:list[tuple[str, str, str, str]] = []
            for body in flagged:
                row:tuple[str, str, str, str]|None = self._flagged_body_row(name, body)
                if row is not None:
                    rows.append(row)
            self._render_table(rows, anchors=("w", "w", "e", "e"))

    def _flagged_body_row(self, system_name:str, body:sqlite3.Row) -> tuple[str, str, str, str]|None:
        """
        One row per body of interest -- name, what's interesting about it, distance, and
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
            # Confirmed via SAASignalsFound -- the genus (or species, once sampled) is known,
            # not a guess, so show its actual name(s) rather than a bare count.
            tags.append(", ".join(r["species"] or r["genus"] for r in active))
            value += sum(self._exobio_row_value(r) for r in active)
        elif not body["flagged_exobio"]:
            predictions:list[dict] = self._best_predictions_for_body(body["id"])
            if predictions:
                tags.append(f"{len(predictions)} species")
                value += sum(p["value_max"] for p in predictions)
            elif body["has_biological_signals"]:
                # FSSBodySignals already confirmed biology is present here -- worth surfacing
                # even before a Scan gives us anything to guess a genus (and thus a value) from.
                tags.append("biological signals")

        if not value and not tags:
            return None # nothing left to do here -- drop it

        designator:str = _body_designator(system_name, body["body_name"])
        return (designator, ", ".join(tags), _distance_str(body["distance_ls"]), _credits(value))

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
        predictions:list[dict] = [] if (active or all_progress) else self._best_predictions_for_body(body_pk)

        if not active and all_progress:
            return # every genus here is fully sampled -- nothing left to do, drop the section

        if not active and not predictions and not self.state.on_foot:
            return

        self._line(f"{self.state.body_name or 'body'} — exobiology")
        if active:
            self._render_table([self._exobio_progress_row(row) for row in active], anchors=("w", "e", "e"), indent=INDENT_PX)
        elif predictions:
            self._render_table([self._predicted_genus_row(slot) for slot in predictions], anchors=("w", "e", "e"), indent=INDENT_PX)
        else:
            self._line("No genus detected yet")

    def _best_predictions_for_body(self, body_pk:int) -> list[dict]:
        """ Best-per-genus predicted slots, capped to biological_signal_count (or
        MAX_PREDICTED_SHOWN if unknown). Genera tied on raw confidence are merged into one
        slot rather than arbitrarily hiding one -- see signal_count_bias.py. """
        all_predictions:list[sqlite3.Row] = self.store.get_genus_predictions_for_body(body_pk)
        if not all_predictions:
            return []

        body:sqlite3.Row|None = self.store.get_body(body_pk)
        signal_count:int|None = body["biological_signal_count"] if body else None
        atmosphere_type:str = (body["atmosphere_type"] if body else None) or ""

        best_per_genus:dict[str, sqlite3.Row] = {}
        for row in all_predictions:
            genus:str = row["genus"]
            preferred_species:list[str] = signal_count_bias.preferred_species_for_tier(genus, signal_count)
            current:sqlite3.Row|None = best_per_genus.get(genus)
            if current is None:
                best_per_genus[genus] = row
                continue
            row_preferred:bool = row["species"] in preferred_species
            current_preferred:bool = current["species"] in preferred_species
            if (row_preferred, row["confidence"]) > (current_preferred, current["confidence"]):
                best_per_genus[genus] = row

        expected_genera:set[str]|None = None
        if signal_count:
            expected_genera = signal_count_bias.expected_genera_for_signal_count(signal_count, atmosphere_type)

        # Tie on raw confidence -> genuinely ambiguous, merge rather than let chain bias pick one.
        by_confidence:list[sqlite3.Row] = sorted(best_per_genus.values(), key=lambda r: -r["confidence"])
        groups:list[list[sqlite3.Row]] = []
        for row in by_confidence:
            if groups and groups[-1][0]["confidence"] == row["confidence"]:
                groups[-1].append(row)
            else:
                groups.append([row])

        def group_key(group:list[sqlite3.Row]) -> tuple:
            any_in_chain:bool = expected_genera is None or any(row["genus"] in expected_genera for row in group)
            return (not any_in_chain, -group[0]["confidence"])

        groups.sort(key=group_key)

        limit:int = signal_count if signal_count else MAX_PREDICTED_SHOWN
        return [self._merge_prediction_group(group) for group in groups[:limit]]

    def _merge_prediction_group(self, group:list[sqlite3.Row]) -> dict:
        ranges:list[tuple[int, int]] = [self._predicted_row_range(row) for row in group]
        return {
            "name": " or ".join(row["species"] or row["genus"] for row in group),
            "confidence": max(row["confidence"] for row in group),
            "value_min": min(r[0] for r in ranges),
            "value_max": max(r[1] for r in ranges),
        }

    def _predicted_row_range(self, row:sqlite3.Row) -> tuple[int, int]:
        """ (min, max) value for a predicted row -- an exact species-narrowed guess collapses to
        a single number (min==max); a bare genus-level guess spans that genus's full known
        range, since the real species present could turn out to be anywhere in it. """
        if row["species"]:
            value:int = exobiology.estimate_confirmed_value(row["genus"], row["species"]) or 0
            return (value, value)
        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(row["genus"])
        return value_range if value_range else (0, 0)

    def _predicted_genus_row(self, slot:dict) -> tuple[str, str, str]:
        """ Pre-DSS guess -- '?' and a confidence percentage mark it as unconfirmed, both of
        which disappear once SAASignalsFound confirms the real genus for this body. """
        return (f"?{slot['name']}", f"({slot['confidence']:.0%})", f"~{_credits_range(slot['value_min'], slot['value_max'])}")

    def _exobio_row_range(self, row:sqlite3.Row) -> tuple[int, int]:
        """ (min, max) value for a confirmed-genus row -- an exact number once the species is
        sampled (min==max); until then, the genus's full known range, since the actual species
        present isn't known yet and could be worth far less (or more) than the range's top. """
        if row["species"]:
            value:int = row["confirmed_value"] or 0
            return (value, value)
        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(row["genus"] or "")
        return value_range if value_range else (0, 0)

    def _exobio_row_value(self, row:sqlite3.Row) -> int:
        """ Top of _exobio_row_range() -- an optimistic scalar for summing a body's total. """
        return self._exobio_row_range(row)[1]

    def _exobio_progress_row(self, row:sqlite3.Row) -> tuple[str, str, str]:
        """
        Progressive detail as we learn more -- genus placeholder becomes the species name once
        confirmed (first sample), and the value estimate becomes the confirmed value at the same
        time, replacing the generic range guess rather than sitting alongside it.
        """
        genus:str = row["genus"] or "biological"
        name:str = row["species"] or f"{genus} sp."
        value_min, value_max = self._exobio_row_range(row)
        if row["species"]:
            return (name, f"{row['samples_taken']}/3", _credits_range(value_min, value_max))
        return (name, "", f"~{_credits_range(value_min, value_max)}")
