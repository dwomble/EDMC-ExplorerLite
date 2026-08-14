"""
Compact panel: plugin_app's Tk frame. Fixed <=60 char width, vertical scrollbar past 5
visible lines, collapses to a single muted line when idle.
"""
import tkinter as tk
import sqlite3
import re
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
MAX_SPECIES_LABEL_CHARS:int = 28 # cap on the "Genus Acies/Aurasus" possible-species label

def _credits(value:int) -> str:
    return hfplus((value, 'num', '? Cr', ' Cr'))

_NUMERIC_PREFIX:re.Pattern = re.compile(r'^-?[\d,]+(?:\.\d+)?')

def _credits_range(value_min:int, value_max:int) -> str:
    """ A single exact credits string when the range has collapsed to one number; otherwise a
    compact min-max range. Drops the min's unit suffix when it matches the max's (e.g.
    "12.2-16.3M Cr" not "12.2M Cr-16.3M Cr") rather than repeating it. """
    if value_min >= value_max:
        return _credits(value_max)
    min_str:str = _credits(value_min)
    max_str:str = _credits(value_max)
    min_match:re.Match|None = _NUMERIC_PREFIX.match(min_str)
    max_match:re.Match|None = _NUMERIC_PREFIX.match(max_str)
    if min_match and max_match and min_str[min_match.end():] == max_str[max_match.end():]:
        return f"{min_str[:min_match.end()]}-{max_str}"
    return f"{min_str}-{max_str}"

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
            self._line(f"{name} — honk needed")
            return

        # Flagged bodies (value/exobio) are shown as soon as each is individually scanned --
        # not gated behind a full-system FSS sweep, since many explorers scan promising bodies
        # directly rather than sweeping every body in the system map first.
        if system["all_bodies_found"]:
            self._line(f"{name} — {system['fss_body_count']} bodies scanned")
        else:
            status:str = "scan needed" if system["honk_hint"] == "worth a full scan" else "done"
            self._line(f"{name} — {system['honk_body_count']} bodies, {system['honk_non_body_count']} signals — {status}")

        flagged:list[sqlite3.Row] = self.store.get_flagged_bodies_for_system(system["id"])
        if not flagged:
            # A confirmed-empty system (e.g. a binary-star-only system) still gets a line so
            # it reads as "already checked, quiet" rather than a leftover question -- anything
            # else with nothing flagged just stays silent, no value in saying so.
            if system["all_bodies_found"] and not self.store.system_has_any_planet(system["id"]):
                self._line("No planets — DSS not required")
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
        value_min:int = 0
        value_max:int = 0

        if body["flagged_value"] and not body["mapped_at"]:
            scan_value:int = max(body["estimated_scan_value"] or 0, body["estimated_mapping_value"] or 0)
            value_min += scan_value
            value_max += scan_value
            if body["type_label"]:
                tags.append(body["type_label"])

        active:list[sqlite3.Row] = [r for r in self.store.get_species_progress_for_body(body["id"]) if not r["completed_at"]]
        if active:
            # Confirmed via SAASignalsFound -- the genus (or species, once sampled) is known,
            # not a guess, so show its actual name(s) rather than a bare count.
            tags.append(", ".join(r["species"] or r["genus"] for r in active))
            for r in active:
                r_min, r_max = self._exobio_row_range(r)
                value_min += r_min
                value_max += r_max
        elif not body["flagged_exobio"]:
            predictions:list[dict] = self._best_predictions_for_body(body["id"])
            if predictions:
                tags.append(", ".join(f"?{p['name']}" for p in predictions))
                value_min += sum(p["value_min"] for p in predictions)
                value_max += sum(p["value_max"] for p in predictions)
            elif body["has_biological_signals"]:
                # FSSBodySignals already confirmed biology is present here -- worth surfacing
                # even before a Scan gives us anything to guess a genus (and thus a value) from.
                count:int = body["biological_signal_count"] or 1
                tags.append(f"{count} biological signal" + ("" if count == 1 else "s"))

        if not value_max and not tags:
            return None # nothing left to do here -- drop it

        designator:str = _body_designator(system_name, body["body_name"])
        return (designator, ", ".join(tags), _distance_str(body["distance_ls"]), _credits_range(value_min, value_max))

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

        # Fill the (scarce) slots group by group. A tied group that fully fits in what's left
        # gets each member its OWN slot -- 2 real signals with 2 confidently-tied genera should
        # show as 2 separate guesses, not 1 merged "A or B" (bug: this used to merge on ANY
        # tie, collapsing a body with signal_count=2 down to a single displayed slot). Only a
        # group that would overflow the remaining budget gets merged into one slot.
        limit:int = signal_count if signal_count else MAX_PREDICTED_SHOWN
        slots:list[dict] = []
        remaining:int = limit
        for group in groups:
            if remaining <= 0:
                break
            if len(group) <= remaining:
                slots.extend(self._merge_prediction_group([row]) for row in group)
                remaining -= len(group)
            else:
                slots.append(self._merge_prediction_group(group))
                remaining = 0
        return slots

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

    def _possible_species_label(self, body_pk:int, genus:str) -> str:
        """ "Bacterium Acies/Aurasus" -- genus is confirmed via SAASignalsFound but not yet
        sampled, so list its still-plausible species from the original Scan-time prediction
        (still in genus_predictions -- confirming the genus doesn't clear it) instead of a
        generic "genus sp." placeholder. Sorted best-confidence-first so truncation keeps the
        most likely names. """
        candidates:list[sqlite3.Row] = sorted(
            (p for p in self.store.get_genus_predictions_for_body(body_pk) if p["genus"] == genus and p["species"]),
            key=lambda p: -p["confidence"],
        )
        if not candidates:
            return f"{genus} sp."
        prefix:str = f"{genus} "
        names:list[str] = [candidates[0]["species"]] + [
            c["species"][len(prefix):] if c["species"].startswith(prefix) else c["species"]
            for c in candidates[1:]
        ]
        return str_truncate("/".join(names), MAX_SPECIES_LABEL_CHARS)

    def _exobio_progress_row(self, row:sqlite3.Row) -> tuple[str, str, str]:
        """
        Progressive detail as we learn more -- genus placeholder becomes the species name once
        confirmed (first sample), and the value estimate becomes the confirmed value at the same
        time, replacing the generic range guess rather than sitting alongside it.
        """
        genus:str = row["genus"] or "biological"
        name:str = row["species"] or self._possible_species_label(row["body_id"], genus)
        value_min, value_max = self._exobio_row_range(row)
        if row["species"]:
            return (name, f"{row['samples_taken']}/3", _credits_range(value_min, value_max))
        return (name, "", f"~{_credits_range(value_min, value_max)}")
