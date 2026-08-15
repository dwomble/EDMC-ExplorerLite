"""
Compact panel: plugin_app's Tk frame. Fixed <=60 char width, vertical scrollbar past the
configured visible-line count (CFG_VISIBLE_LINES), collapses to a single muted line when idle.
"""
import tkinter as tk
import sqlite3
import re
from typing import Callable

from config import config # type: ignore

import explorer.utils.th as th
from explorer.utils.misc import hfplus, str_truncate

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.valuation import exobiology, exobiology_data, signal_count_bias
from explorer.constants import CFG_VISIBLE_LINES, DEFAULT_VISIBLE_LINES

WIDTH_CHARS:int = 60
LINE_HEIGHT_PX:int = 18 # approximate for the default EDMC font; tune once seen in a real window
MAX_PREDICTED_SHOWN:int = 3 # fallback cap on predicted candidates per body, only used until
# FSSBodySignals tells us the body's real biological_signal_count (see _best_predictions_for_body)
INDENT_PX:int = 14 # left offset for a table nested under its own header line (e.g. per-body biologicals)
MAX_SPECIES_LABEL_CHARS:int = 28 # cap on the "Genus Acies/Aurasus" possible-species label
MAX_MERGED_TAG_CHARS:int = 40 # above this, a 3+-way merged genus list collapses to just a count
GRAVITY_MS2_PER_G:float = 9.797759 # matches genus_prediction.py's own constant, not the textbook 9.80665

def _visible_lines_px() -> int:
    return config.get_int(CFG_VISIBLE_LINES, default=DEFAULT_VISIBLE_LINES) * LINE_HEIGHT_PX

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

def _gravity_str(surface_gravity_ms2:float|None) -> str:
    return "?g" if surface_gravity_ms2 is None else f"{surface_gravity_ms2 / GRAVITY_MS2_PER_G:.2f}g"

def _sampling_distance_str(genera:list[str]) -> str:
    """ Minimum walking distance between samples -- a range when a merged slot spans genera
    with different requirements, since which one it actually is isn't confirmed yet. """
    distances:list[int] = [d for d in (exobiology_data.genus_min_distance(g) for g in genera) if d is not None]
    if not distances:
        return "?"
    return f"{min(distances)}m" if min(distances) == max(distances) else f"{min(distances)}-{max(distances)}m"

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
        self.scroll:th.ScrollableFrame = th.ScrollableFrame(self.frame, maxheight=_visible_lines_px())
        self.scroll.grid(row=0, column=0, sticky=tk.EW)
        self.history_button:th.Button = th.Button(self.frame, text="History", command=self._open_history)
        self.history_button.grid(row=1, column=0, sticky=tk.EW)

        self.refresh()

    def _open_history(self) -> None:
        if self.on_history_open:
            self.on_history_open()

    def _line(self, text:str) -> None:
        th.Label(self.scroll.interior, text=str_truncate(text, WIDTH_CHARS), anchor="w", justify="left", pady=0).pack(fill=tk.X)

    def _render_table(self, rows:list[tuple[str, ...]], anchors:tuple[str, ...], indent:int = 0) -> None:
        """
        Grid `rows` into one Frame -- packed into the scroll as a single "line" (consistent
        with _line()) -- so Tk's grid geometry manager aligns every column to its widest cell.
        A plain space-joined string only lines up columns if the font happens to be monospace,
        which EDMC's theme doesn't guarantee. pady=0 keeps rows tight -- Tk's default Label
        padding adds up fast once a body lists several species.
        """
        if not rows:
            return
        table:th.Frame = th.Frame(self.scroll.interior)
        for r, row in enumerate(rows):
            last:int = len(row) - 1
            for c, (text, anchor) in enumerate(zip(row, anchors)):
                sticky:str = tk.W if anchor == "w" else tk.E
                pad:tuple[int, int] = (0, 0) if c == last else (0, 8)
                th.Label(table, text=text, anchor=anchor, pady=0).grid(row=r, column=c, sticky=sticky, padx=pad)
        table.pack(fill=tk.X, padx=(indent, 0))

    def refresh(self) -> None:
        self.scroll.configure(maxheight=_visible_lines_px()) # live prefs change -- no restart needed
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

        hbc:int|None = system["honk_body_count"]
        if hbc is None:
            self._line(f"{name} — honk needed")
            return

        # Flagged bodies (value/exobio) are shown as soon as each is individually scanned --
        # not gated behind a full-system FSS sweep, since many explorers scan promising bodies
        # directly rather than sweeping every body in the system map first.
        if system["all_bodies_found"]:
            self._line(f"{name} — {hbc} bod{'ies' if hbc != 1 else 'y'} — scan complete")
        else:
            status:str = "scan needed" if system["honk_hint"] == "worth a full scan" else "done"
            self._line(f"{name} — {hbc} bod{'ies' if hbc != 1 else 'y'} — {status}")

        flagged:list[sqlite3.Row] = self.store.get_flagged_bodies_for_system(system["id"])
        if flagged:
            rows:list[tuple[str, str, str, str, str]] = []
            for body in flagged:
                row:tuple[str, str, str, str, str]|None = self._flagged_body_row(name, body)
                if row is not None:
                    rows.append(row)
            self._render_table(rows, anchors=("w", "e", "e", "e", "w"))

    def _flagged_body_row(self, system_name:str, body:sqlite3.Row) -> tuple[str, str, str, str, str]|None:
        """
        One row per body of interest -- name, distance, gravity, total remaining value, and
        what's biologically interesting about it. A body drops off this list entirely once
        there's nothing left to actually do there (mapped, and any exobiology fully sampled) --
        it's a to-do list, not a permanent record (see history for that).
        """
        species_desc:str = ""
        value_min:int = 0
        value_max:int = 0

        if body["flagged_value"] and not body["mapped_at"]:
            scan_value:int = max(body["estimated_scan_value"] or 0, body["estimated_mapping_value"] or 0)
            value_min += scan_value
            value_max += scan_value

        active:list[sqlite3.Row] = [r for r in self.store.get_species_progress_for_body(body["id"]) if not r["completed_at"]]
        if active:
            # Confirmed via SAASignalsFound -- the genus is known, not a guess. Species isn't
            # sampled yet, but the earlier Scan-time prediction already narrowed down which
            # ones are still plausible (see _possible_species_label) -- don't throw that away
            # and fall back to a bare genus name just because the genus itself is now certain.
            names:list[str] = [r["species"] or self._possible_species_label(body["id"], r["genus"]) for r in active]
            species_desc = ", ".join(names)
            for r in active:
                r_min, r_max = self._exobio_row_range(r)
                value_min += r_min
                value_max += r_max
        elif not body["flagged_exobio"]:
            predictions:list[dict] = self._best_predictions_for_body(body["id"])
            if predictions:
                # A confirmed biological signal (FSSBodySignals) means a real genus is
                # certainly here -- only WHICH one is unconfirmed, so the "?" (which reads as
                # doubt about existence, not just identity) only belongs on a purely
                # speculative Scan-based guess with no confirmed signal at all.
                prefix:str = "" if body["has_biological_signals"] else "?"
                species_desc = f"{prefix}{self._collapse_prediction_names(predictions)}"
                value_min += sum(p["value_min"] for p in predictions)
                value_max += sum(p["value_max"] for p in predictions)
            elif body["has_biological_signals"]:
                # FSSBodySignals already confirmed biology is present here -- worth surfacing
                # even before a Scan gives us anything to guess a genus (and thus a value) from.
                count:int = body["biological_signal_count"] or 1
                species_desc = f"{count} biological signal" + ("" if count == 1 else "s")

        if not value_max and not species_desc:
            return None # nothing left to do here -- drop it

        designator:str = _body_designator(system_name, body["body_name"])
        if body["type_label"]:
            designator = f"{designator} ({body['type_label']})"
        return (
            designator, _distance_str(body["distance_ls"]), _gravity_str(body["surface_gravity"]),
            _credits_range(value_min, value_max), species_desc,
        )

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
            body:sqlite3.Row|None = self.store.get_body(body_pk)
            confirmed_signal:bool = bool(body and body["has_biological_signals"])
            self._render_table(
                [self._predicted_genus_row(slot, confirmed_signal) for slot in predictions], anchors=("w", "e", "e"), indent=INDENT_PX
            )
        else:
            self._line("No genus detected yet")

    def _best_predictions_for_body(self, body_pk:int) -> list[dict]:
        """ Best-per-genus predicted slots, capped to biological_signal_count (or
        MAX_PREDICTED_SHOWN if unknown). Within a genus, several species often tie at the same
        top confidence -- one is picked (chain-tier preference) as the display name, but the
        value range spans every tied alternate, not just the one shown, so a silent single pick
        doesn't understate what's genuinely still possible (e.g. a lower-value species winning
        the tiebreak while a much higher-value one ties right alongside it).

        Each chain tier (see signal_count_bias.py) counts as ONE unit, not several -- a tier can
        be ambiguous between its own alternatives (e.g. Osseus-or-Tubus), but that's still a
        single real signal slot. Units are grouped by RAW confidence exactly like before, and a
        group containing a chain unit is given priority over a same-or-lower-confidence group
        that's purely non-chain (the signal-count pattern is stronger evidence than a marginal
        condition-matching gap). But within a single confidence-TIED group -- genuinely
        equally-scored candidates -- chain membership only decides which subset gets an
        individual slot when the group is too big to fit; it never lets the chain silently pick
        one tied candidate over another as if it were certain (that's what merging is for). A
        group too big for the remaining slots keeps as many individual slots as it can
        (chain-tier order first) and folds only the true excess into one final merged slot. """
        all_predictions:list[sqlite3.Row] = self.store.get_genus_predictions_for_body(body_pk)
        if not all_predictions:
            return []

        body:sqlite3.Row|None = self.store.get_body(body_pk)
        signal_count:int|None = body["biological_signal_count"] if body else None
        atmosphere_type:str = (body["atmosphere_type"] if body else None) or ""

        by_genus:dict[str, list[sqlite3.Row]] = {}
        for row in all_predictions:
            by_genus.setdefault(row["genus"], []).append(row)

        genus_slots:dict[str, dict] = {}
        for genus, rows in by_genus.items():
            preferred_species:list[str] = signal_count_bias.preferred_species_for_tier(genus, signal_count)
            best_confidence:float = max(r["confidence"] for r in rows)
            tied:list[sqlite3.Row] = [r for r in rows if r["confidence"] == best_confidence]
            representative:sqlite3.Row = next((r for r in tied if r["species"] in preferred_species), tied[0])
            ordered:list[sqlite3.Row] = [representative] + [r for r in tied if r is not representative]
            species_names:list[str] = [r["species"] for r in ordered if r["species"]]
            ranges:list[tuple[int, int]] = [self._predicted_row_range(r) for r in tied]
            genus_slots[genus] = {
                "genera": [genus],
                "name": self._join_species_names(genus, species_names) if species_names else genus,
                "confidence": best_confidence,
                "value_min": min(r[0] for r in ranges),
                "value_max": max(r[1] for r in ranges),
            }

        # Consolidate each chain tier's candidate genus/genera into one unit; whatever's left
        # (genera outside every tier, or the chain heuristic doesn't apply here at all) stays
        # on its own. `chain_tier` is just an internal sort key -- dropped once merged.
        claimed:set[str] = set()
        units:list[dict] = []
        chain_applies:bool = bool(signal_count) and atmosphere_type not in signal_count_bias.CHAIN_EXCEPTION_ATMOSPHERES
        if chain_applies:
            assert signal_count is not None
            for tier in range(1, min(signal_count, signal_count_bias.MAX_CHAIN_SIGNAL_COUNT) + 1):
                tier_genera:list[str] = [g for g in signal_count_bias.SIGNAL_COUNT_TIER_GENERA.get(tier, []) if g in genus_slots]
                if not tier_genera:
                    continue # this tier's genus/genera don't match this body's conditions at all -- can't force it
                unit:dict = self._merge_prediction_group([genus_slots[g] for g in tier_genera])
                unit["chain_tier"] = tier
                units.append(unit)
                claimed.update(tier_genera)
        for genus, slot in genus_slots.items():
            if genus not in claimed:
                units.append({**slot, "chain_tier": None})

        by_confidence:list[dict] = sorted(units, key=lambda u: -u["confidence"])
        groups:list[list[dict]] = []
        for unit in by_confidence:
            if groups and groups[-1][0]["confidence"] == unit["confidence"]:
                groups[-1].append(unit)
            else:
                groups.append([unit])
        for group in groups:
            group.sort(key=lambda u: u["chain_tier"] if u["chain_tier"] is not None else 999)

        def group_key(group:list[dict]) -> tuple:
            any_chain:bool = any(u["chain_tier"] is not None for u in group)
            return (not any_chain, -group[0]["confidence"])

        groups.sort(key=group_key)

        limit:int = signal_count if signal_count else MAX_PREDICTED_SHOWN
        slots:list[dict] = []
        remaining:int = limit
        for group in groups:
            if remaining <= 0:
                break
            if len(group) <= remaining:
                slots.extend(self._merge_prediction_group([unit]) for unit in group)
                remaining -= len(group)
            elif remaining == 1:
                slots.append(self._merge_prediction_group(group))
                remaining = 0
            else:
                slots.extend(self._merge_prediction_group([unit]) for unit in group[:remaining - 1])
                slots.append(self._merge_prediction_group(group[remaining - 1:]))
                remaining = 0
        return slots

    def _collapse_prediction_names(self, items:list[dict]) -> str:
        """ Comma-joined names read shorter and cleaner than "a or b or c" (see conversation).
        3+ items is usually too long to name in full -- fall back to just the distinct genus
        names, or if even that overflows the panel, just a count. Shared by _merge_prediction_
        group() (merging tied alternates into one slot) and _flagged_body_row() (joining the
        body's full slot list into one line). """
        if len(items) <= 2:
            return ", ".join(item["name"] for item in items)
        genera:list[str] = list(dict.fromkeys(genus for item in items for genus in item["genera"]))
        joined:str = ", ".join(genera)
        return joined if len(joined) <= MAX_MERGED_TAG_CHARS else f"{len(genera)} possible genera"

    def _merge_prediction_group(self, group:list[dict]) -> dict:
        return {
            "name": self._collapse_prediction_names(group),
            "confidence": max(slot["confidence"] for slot in group),
            "value_min": min(slot["value_min"] for slot in group),
            "value_max": max(slot["value_max"] for slot in group),
            "genera": [genus for slot in group for genus in slot["genera"]],
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

    def _predicted_genus_row(self, slot:dict, confirmed_signal:bool) -> tuple[str, str, str]:
        """ Pre-DSS guess -- the '?' only applies when even the SIGNAL's existence is
        speculative (no FSSBodySignals yet); once a signal is confirmed, a real genus is
        certainly here -- only which one is still open. """
        prefix:str = "" if confirmed_signal else "?"
        return (
            f"{prefix}{slot['name']}", _sampling_distance_str(slot["genera"]),
            f"~{_credits_range(slot['value_min'], slot['value_max'])}",
        )

    def _exobio_row_range(self, row:sqlite3.Row) -> tuple[int, int]:
        """ (min, max) value for a confirmed-genus row -- an exact number once the species is
        sampled (min==max); until then, the genus's full known range, since the actual species
        present isn't known yet and could be worth far less (or more) than the range's top. """
        if row["species"]:
            value:int = row["confirmed_value"] or 0
            return (value, value)
        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(row["genus"] or "")
        return value_range if value_range else (0, 0)

    def _join_species_names(self, genus:str, names:list[str]) -> str:
        """ "Bacterium Cerbrus/Tela" -- first name kept in full, genus prefix stripped from the
        rest (repeating it is redundant once the first name has already established it). """
        prefix:str = f"{genus} "
        joined:list[str] = [names[0]] + [n[len(prefix):] if n.startswith(prefix) else n for n in names[1:]]
        return str_truncate("/".join(joined), MAX_SPECIES_LABEL_CHARS)

    def _possible_species_label(self, body_pk:int, genus:str) -> str:
        """ Genus is confirmed via SAASignalsFound but not yet sampled, so list its still-
        plausible species from the original Scan-time prediction (still in genus_predictions --
        confirming the genus doesn't clear it) instead of a generic "genus sp." placeholder.
        Sorted best-confidence-first so truncation keeps the most likely names. """
        candidates:list[sqlite3.Row] = sorted(
            (p for p in self.store.get_genus_predictions_for_body(body_pk) if p["genus"] == genus and p["species"]),
            key=lambda p: -p["confidence"],
        )
        if not candidates:
            return f"{genus} sp."
        return self._join_species_names(genus, [c["species"] for c in candidates])

    def _exobio_progress_row(self, row:sqlite3.Row) -> tuple[str, str, str]:
        """
        Progressive detail as we learn more -- genus placeholder becomes the species name once
        confirmed (first sample), and the value estimate becomes the confirmed value at the same
        time, replacing the generic range guess rather than sitting alongside it.
        """
        genus:str = row["genus"] or "biological"
        name:str = row["species"] or self._possible_species_label(row["body_id"], genus)
        value_min, value_max = self._exobio_row_range(row)
        distance:str = _sampling_distance_str([genus])
        if row["species"]:
            return (name, distance, _credits_range(value_min, value_max))
        return (name, distance, f"~{_credits_range(value_min, value_max)}")
