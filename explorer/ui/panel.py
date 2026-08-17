"""
Compact panel: plugin_app's Tk frame. Fixed <=60 char width, vertical scrollbar past the
configured visible-line count (CFG_VISIBLE_LINES), collapses to a single muted line when idle.
"""
import tkinter as tk
import tkinter.font as tkfont
import sqlite3
import re
from typing import Callable

from config import config # type: ignore

import explorer.utils.th as th
from explorer.utils.misc import hfplus, str_truncate

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.valuation import cartography, exobiology, exobiology_data, signal_count_bias
from explorer.constants import CFG_VISIBLE_LINES, DEFAULT_VISIBLE_LINES, CFG_PANEL_ENABLED, PLUGIN_NAME

HISTORY_GLYPH:str = "\U0001F553" # clock face
PANEL_SHOWN_GLYPH:str = "\U0001F648" # see-no-evil monkey -- "pause" analog while visible
PANEL_HIDDEN_GLYPH:str = "\U0001F441" # eye -- "play" analog while hidden

WIDTH_CHARS:int = 60
LINE_HEIGHT_PX:int = 18 # approximate for the default EDMC font; tune once seen in a real window
MAX_PREDICTED_SHOWN:int = 3 # fallback cap on predicted candidates per body, only used until
# FSSBodySignals tells us the body's real biological_signal_count (see _best_predictions_for_body)
INDENT_PX:int = 14 # left offset for a table nested under its own header line (e.g. per-body biologicals)
MAX_SPECIES_LABEL_CHARS:int = 28 # cap on the "Genus Acies/Aurasus" possible-species label
MAX_FULL_NAME_CHARS:int = 24 # above this, try abbreviated genus codes before giving up
MAX_MERGED_TAG_CHARS:int = 32 # above this even abbreviated, collapse to just a genus count
SAMPLES_REQUIRED:int = 3 # every species needs exactly 3 real samples (Log/Sample x2) to complete -- see handlers_exobiology.py
GRAVITY_MS2_PER_G:float = 9.797759 # matches genus_prediction.py's own constant, not the textbook 9.80665

def _visible_lines_px() -> int:
    return config.get_int(CFG_VISIBLE_LINES, default=DEFAULT_VISIBLE_LINES) * LINE_HEIGHT_PX

def _credits(value:int) -> str:
    return hfplus((value, 'num', '? Cr', ' Cr'))

def _header_credits(value:int) -> str:
    """ Here 0 means "nothing pending", not "unknown". """
    return "0 Cr" if value == 0 else _credits(value)

_NUMERIC_PREFIX:re.Pattern = re.compile(r'^-?[\d,]+(?:\.\d+)?')

def _credits_range(min_val:int, max_val:int) -> str:
    """ A single exact credits string when the range has collapsed to one number; otherwise a
    compact min-max range. Drops the min's unit suffix when it matches the max's (e.g.
    "12.2-16.3M Cr" not "12.2M Cr-16.3M Cr") rather than repeating it. """
    if min_val >= max_val:
        return _credits(max_val)
    min_str:str = _credits(min_val)
    max_str:str = _credits(max_val)
    min_match:re.Match|None = _NUMERIC_PREFIX.match(min_str)
    max_match:re.Match|None = _NUMERIC_PREFIX.match(max_str)
    if min_match and max_match and min_str[min_match.end():] == max_str[max_match.end():]:
        return f"{min_str[:min_match.end()]}-{max_str}"
    return f"{min_str}-{max_str}"

def _distance_str(dist:float|None) -> str:
    return hfplus((dist, 'num', '? ls', ' ls'))

def _gravity_str(gravity:float|None) -> str:
    return "?g" if gravity is None else f"{gravity / GRAVITY_MS2_PER_G:.2f}g"

def _sampling_distance_str(genera:list[str]) -> str:
    """ Minimum walking distance between samples -- a range when a merged slot spans genera
    with different requirements, since which one it actually is isn't confirmed yet. """
    distances:list[int] = [d for d in (exobiology_data.genus_min_distance(g) for g in genera) if d is not None]
    if not distances:
        return "?"

    return f"{min(distances)}m" if min(distances) == max(distances) else f"{min(distances)}-{max(distances)}m"

def _next_actions(store:ExplorerStore, system_id:int) -> tuple[bool, bool]:
    """ (needs_dss, needs_sample) for the system. """
    needs_dss:bool = False
    needs_sample:bool = False
    for body in store.get_flagged_bodies_for_system(system_id):
        if not body["mapped_at"]:
            needs_dss = True
            continue
        if any(not p["completed_at"] for p in store.get_species_progress_for_body(body["id"])):
            needs_sample = True
    return needs_dss, needs_sample

def system_status_text(store:ExplorerStore, system:sqlite3.Row) -> str:
    """ No system name -- shared as-is with the overlay. """
    if system["honk_body_count"] is None:
        return "Honk"

    if system["honk_hint"] != "worth a full scan":
        return "Done" # not worth a full scan -- nothing else to do here

    if not system["all_bodies_found"]:
        return "FSS"

    needs_dss, needs_sample = _next_actions(store, system["id"])
    if needs_dss and needs_sample:
        return "DSS + Sample"
    if needs_dss:
        return "DSS"
    if needs_sample:
        return "Sample"
    return "Done"

def system_body_count_text(system:sqlite3.Row) -> str:
    """ "N bodies" once honked, not the FSS progress. """
    hbc:int|None = system["honk_body_count"]
    if hbc is None:
        return ""
    return f"{hbc} bod{'ies' if hbc != 1 else 'y'}"

def system_header_prefix(system:sqlite3.Row) -> str:
    """ Header line, minus the state itself. """
    body_count:str = system_body_count_text(system)
    return f"{system['name']} — {body_count} —" if body_count else f"{system['name']} —"

def system_header_line(store:ExplorerStore, system:sqlite3.Row) -> str:
    """ Plain-text header; the panel bolds the state. """
    return f"{system_header_prefix(system)} {system_status_text(store, system)}"

def _bold_font() -> tkfont.Font:
    default:tkfont.Font = tkfont.nametofont("TkDefaultFont")
    return tkfont.Font(family=default.actual("family"), size=default.actual("size"), weight="bold")

def flagged_body_sort_key(body:sqlite3.Row) -> bool:
    """ Biological first, shared so panel/overlay agree. """
    biological:bool = bool(body["has_biological_signals"] == 1 or body["flagged_exobio"] or body["has_prediction"])
    return not biological

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

        self._panel_enabled:bool = config.get_bool(CFG_PANEL_ENABLED, default=True)

        self.frame:th.Frame = th.Frame(parent)
        self.frame.columnconfigure(0, weight=1)

        # grid, not pack -- th.Base's pack() renders light/dark widget pairs twice
        header:th.Frame = th.Frame(self.frame) # always shown -- only self.scroll below hides
        header.grid(row=0, column=0, sticky=tk.EW)
        header.columnconfigure(0, weight=1) # title/cart/exo share slack, spreading them out
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=1)

        self._title_font:tkfont.Font = _bold_font()
        self.title_label:th.Label = th.Label(header, text=PLUGIN_NAME, font=self._title_font, anchor="w")
        self.title_label.grid(row=0, column=0, sticky=tk.W)

        self.cart_value_label:th.Label = th.Label(header, text=_header_credits(0), anchor="w")
        self.cart_value_label.grid(row=0, column=1, sticky=tk.W)
        th.Tooltip(self.cart_value_label, "Pending cartography value")

        self.exo_value_label:th.Label = th.Label(header, text=_header_credits(0), anchor="w")
        self.exo_value_label.grid(row=0, column=2, sticky=tk.W)
        th.Tooltip(self.exo_value_label, "Pending exobiology value")

        self.history_button:th.Button = th.Button(header, text=HISTORY_GLYPH, width=3, command=self._open_history)
        self.history_button.grid(row=0, column=3, sticky=tk.E)
        th.Tooltip(self.history_button, "Open history")

        self.toggle_button:th.Button = th.Button(header, text=self._toggle_glyph(), width=3, command=self._toggle_panel)
        self.toggle_button.grid(row=0, column=4, sticky=tk.E)
        self._toggle_tooltip:th.Tooltip = th.Tooltip(self.toggle_button, self._toggle_tooltip_text())

        self.scroll:th.ScrollableFrame = th.ScrollableFrame(self.frame, maxheight=_visible_lines_px())
        self.scroll.grid(row=1, column=0, sticky=tk.EW)
        self.scroll.interior.columnconfigure(0, weight=1) # each row below is gridded, not packed -- see refresh()
        if not self._panel_enabled:
            self.scroll.grid_forget()

        self._pending:list[tuple] = [] # lines/tables queued by _line()/_render_table() during the current refresh()
        self._last_rendered:list[tuple] = [] # what's actually on screen right now, one entry per row widget
        self._row_widgets:list[tk.Widget] = [] # the live widget for each _last_rendered row, same order

        self.refresh()

    def _open_history(self) -> None:
        if self.on_history_open:
            self.on_history_open()

    def _toggle_glyph(self) -> str:
        return PANEL_SHOWN_GLYPH if self._panel_enabled else PANEL_HIDDEN_GLYPH

    def _toggle_tooltip_text(self) -> str:
        return "Hide panel" if self._panel_enabled else "Show panel"

    def _toggle_panel(self) -> None:
        """ Shows/hides content; collection keeps going. """
        self._panel_enabled = not self._panel_enabled
        config.set(CFG_PANEL_ENABLED, self._panel_enabled)
        self.toggle_button.configure(text=self._toggle_glyph())
        self._toggle_tooltip.set_text(self._toggle_tooltip_text())
        if self._panel_enabled:
            self.scroll.grid(row=1, column=0, sticky=tk.EW)
            self.refresh()
        else:
            self.scroll.grid_forget()

    def _update_header_totals(self) -> None:
        cmdr_id:int|None = self.state.cmdr_id
        cart:int = self.store.get_pending_cartography_value(cmdr_id) if cmdr_id is not None else 0
        exo:int = self.store.get_pending_exobiology_value(cmdr_id) if cmdr_id is not None else 0
        self.cart_value_label.configure(text=_header_credits(cart))
        self.exo_value_label.configure(text=_header_credits(exo))

    def _line(self, text:str) -> None:
        self._pending.append(("line", str_truncate(text, WIDTH_CHARS)))

    def _header_line(self, prefix:str, state:str) -> None:
        self._pending.append(("header", str_truncate(prefix, WIDTH_CHARS), state))

    def _render_table(self, rows:list[tuple[str, ...]], anchors:tuple[str, ...], indent:int = 0) -> None:
        if rows:
            self._pending.append(("table", tuple(rows), anchors, indent))

    def _materialize_row(self, command:tuple, row:int) -> tk.Widget:
        """ Grid (not pack) so a single row can be replaced in place without re-sequencing others. """
        if command[0] == "line":
            widget:tk.Widget = th.Label(self.scroll.interior, text=command[1], anchor="w", justify="left", pady=0)
            widget.grid(row=row, column=0, sticky=tk.EW)
            return widget

        if command[0] == "header":
            _, prefix, state = command
            header:th.Frame = th.Frame(self.scroll.interior)
            th.Label(header, text=prefix, anchor="w", pady=0).grid(row=0, column=0, sticky=tk.W)
            th.Label(header, text=state, anchor="w", pady=0, font=self._title_font).grid(row=0, column=1, sticky=tk.W, padx=(4, 0))
            header.grid(row=row, column=0, sticky=tk.EW)
            return header

        _, rows, anchors, indent = command
        table:th.Frame = th.Frame(self.scroll.interior)
        for r, table_row in enumerate(rows):
            last:int = len(table_row) - 1
            for c, (text, anchor) in enumerate(zip(table_row, anchors)):
                sticky:str = tk.W if anchor == "w" else tk.E
                pad:tuple[int, int] = (0, 0) if c == last else (0, 8)
                th.Label(table, text=text, anchor=anchor, pady=0).grid(row=r, column=c, sticky=sticky, padx=pad)
        table.grid(row=row, column=0, sticky=tk.EW, padx=(indent, 0))
        return table

    def refresh(self) -> None:
        """ Diffs _pending against _last_rendered row by row -- only rebuilds rows that changed. """
        self._update_header_totals() # header stays live even while the rest is hidden

        if not self._panel_enabled:
            return # hidden -- _toggle_panel() rebuilds fully once shown again

        self.scroll.configure(maxheight=_visible_lines_px()) # live prefs change -- no restart needed

        self._pending = []
        system:sqlite3.Row|None = self.store.get_system(self.state.system_id) if self.state.system_id is not None else None
        if system is None:
            self._line("Explorer — idle")
        else:
            self._render_system_summary(system)

        for i, command in enumerate(self._pending):
            if i < len(self._last_rendered) and command == self._last_rendered[i]:
                continue # unchanged -- leave the existing widget exactly as it is
            if i < len(self._row_widgets):
                self._row_widgets[i].destroy()
                self._row_widgets[i] = self._materialize_row(command, i)
            else:
                self._row_widgets.append(self._materialize_row(command, i))

        while len(self._row_widgets) > len(self._pending): # fewer rows than last time -- drop the leftovers
            self._row_widgets.pop().destroy()

        self._last_rendered = self._pending

    def _render_system_summary(self, system:sqlite3.Row) -> None:
        self._header_line(system_header_prefix(system), system_status_text(self.store, system))
        if system["honk_body_count"] is None:
            return

        name:str = system["name"]
        # Current body's exobiology detail nests under its own row, not after the whole table
        anchors:tuple = ("w", "e", "e", "e", "w")
        flagged:list[sqlite3.Row] = sorted(self.store.get_flagged_bodies_for_system(system["id"]), key=flagged_body_sort_key)
        pending_rows:list = []
        current_row_shown:bool = False
        for body in flagged:
            row:tuple[str, str, str, str, str]|None = self._flagged_body_row(name, body)
            if row is None:
                continue
            if self.state.body_id is not None and body["body_id"] == self.state.body_id:
                if pending_rows:
                    self._render_table(pending_rows, anchors=anchors)
                    pending_rows = []
                self._render_table([row], anchors=anchors)
                self._render_exobiology_section()
                current_row_shown = True
            else:
                pending_rows.append(row)
        if pending_rows:
            self._render_table(pending_rows, anchors=anchors)

        # Current body may not be in the flagged list at all (e.g. on-foot, uninteresting body)
        if not current_row_shown and self.state.body_id is not None and self.state.cmdr_id is not None:
            self._render_exobiology_section()

    def _flagged_body_row(self, system_name:str, body:sqlite3.Row) -> tuple[str, str, str, str, str]|None:
        """ A body drops off this to-do list once nothing's left to do there. Shown value is
        Full (bonus-included) -- what the body would actually pay out, not the base/progression
        number (see _exobio_progress_row/history view for the Base/Full split). """
        species_desc:str = ""
        value_min:int = 0
        value_max:int = 0
        was_footfalled:bool = bool(body["was_footfalled"])

        if body["flagged_value"] and not body["mapped_at"]:
            scan_full:int = cartography.scan_value_with_bonus(body["estimated_scan_value"] or 0, bool(body["was_discovered"]))
            mapping_full:int = cartography.mapping_value_for_eligibility(body["estimated_mapping_value"] or 0, bool(body["was_mapped"]))
            cart_value:int = max(scan_full, mapping_full)
            value_min += cart_value
            value_max += cart_value

        all_progress:list[sqlite3.Row] = self.store.get_species_progress_for_body(body["id"])
        active:list[sqlite3.Row] = [r for r in all_progress if not r["completed_at"]]
        fully_sampled:bool = bool(all_progress) and not active
        if active:
            # Compact count, not a full name list (see _exobio_progress_row for names, on-body)
            species_desc = f"{len(all_progress) - len(active)} of {len(all_progress)} scanned"
            for r in active:
                r_min, r_max = self._exobio_row_range(r)
                value_min += exobiology.with_first_logged_bonus(r_min, was_footfalled)
                value_max += exobiology.with_first_logged_bonus(r_max, was_footfalled)

        predictions:list[dict] = self._best_predictions_for_body(body["id"]) if not active and not body["flagged_exobio"] else []

        if predictions:
            # "?" only for a purely speculative guess -- a confirmed signal means a genus IS here
            prefix:str = "" if body["has_biological_signals"] else "?"
            signal_count:int|None = body["biological_signal_count"] # ground truth count, vs. the guessed kinds below
            collapsed:str = self._collapse_prediction_names(predictions)
            sep:str = "of" if collapsed.endswith("possible genera") else "–" # "N of M possible genera" reads clearer than "N – M"
            count_prefix:str = f"{signal_count} {sep} " if signal_count else ""
            species_desc = f"{count_prefix}{prefix}{collapsed}"
            value_min += exobiology.with_first_logged_bonus(sum(p["value_min"] for p in predictions), was_footfalled)
            value_max += exobiology.with_first_logged_bonus(sum(p["value_max"] for p in predictions), was_footfalled)

        if not active and not predictions and body["has_biological_signals"] and not fully_sampled:
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
        """ Silent for an uninteresting body unless on-foot there. No header -- caller nests this under the body's own row. """
        assert self.state.cmdr_id is not None and self.state.system_id is not None and self.state.body_id is not None
        body_pk:int = self.store.get_or_create_body(self.state.cmdr_id, self.state.system_id, self.state.body_id, self.state.body_name)

        all_progress:list[sqlite3.Row] = self.store.get_species_progress_for_body(body_pk)
        active:list[sqlite3.Row] = [row for row in all_progress if not row["completed_at"]]
        predictions:list[dict] = [] if (active or all_progress) else self._best_predictions_for_body(body_pk)

        if not active and all_progress:
            return # every genus here is fully sampled -- nothing left to do, drop the section

        if not active and not predictions and not self.state.on_foot:
            return

        body:sqlite3.Row|None = self.store.get_body(body_pk)
        was_footfalled:bool = bool(body and body["was_footfalled"])

        if active:
            self._render_table(
                [self._exobio_progress_row(row, was_footfalled) for row in active], anchors=("w", "e", "e", "e"), indent=INDENT_PX
            )
            return

        if predictions:
            confirmed_signal:bool = bool(body and body["has_biological_signals"])
            self._render_table(
                [self._predicted_genus_row(slot, confirmed_signal, was_footfalled) for slot in predictions],
                anchors=("w", "e", "e"), indent=INDENT_PX,
            )
            return


    def _best_predictions_for_body(self, body_pk:int) -> list[dict]:
        """ Best-per-genus predicted slots, capped to biological_signal_count (or MAX_PREDICTED_SHOWN).
        Chain tiers count as one slot each; ties beyond the cap fold into one merged slot. """
        all_predictions:list[sqlite3.Row] = self.store.get_genus_predictions_for_body(body_pk)
        if not all_predictions:
            return []

        body:sqlite3.Row|None = self.store.get_body(body_pk)
        if body and body["has_biological_signals"] == 0:
            return [] # confirmed zero signals beats a stale pre-Scan guess

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

        # Consolidate each chain tier's candidates into one unit; the rest stay on their own
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
            if remaining <= 0: break
            if len(group) <= remaining:
                slots.extend(self._merge_prediction_group([unit]) for unit in group)
                remaining -= len(group)
                continue

            if remaining == 1:
                slots.append(self._merge_prediction_group(group))
                remaining = 0
                continue

            slots.extend(self._merge_prediction_group([unit]) for unit in group[:remaining - 1])
            slots.append(self._merge_prediction_group(group[remaining - 1:]))
            remaining = 0
        return slots

    def _collapse_prediction_names(self, items:list[dict]) -> str:
        """ Full, abbreviated, then a bare genus count. """
        if len(items) <= 2:
            full:str = ", ".join(item["name"] for item in items)
            if len(full) <= MAX_FULL_NAME_CHARS:
                return full

        abbreviated:str = "/".join(self._abbreviated_name(item) for item in items)
        if len(abbreviated) <= MAX_MERGED_TAG_CHARS:
            return abbreviated

        genera:list[str] = list(dict.fromkeys(genus for item in items for genus in item["genera"]))
        return f"{len(genera)} possible genera" # distinct genera, not slots

    def _abbreviated_name(self, item:dict) -> str:
        """ Abbreviates via the radar's own genus code. """
        genus:str = item["genera"][0]
        if len(item["genera"]) != 1 or not item["name"].startswith(genus):
            return item["name"] # a merged multi-genus item -- nothing single to abbreviate
        code:str = exobiology_data.genus_code(genus).capitalize() + "."
        return f"{code}{item['name'][len(genus):]}"

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

    def _predicted_genus_row(self, slot:dict, confirmed_signal:bool, was_footfalled:bool) -> tuple[str, str, str]:
        """ '?' only when the signal itself is unconfirmed; '~' only when a value range remains.
        Value shown is Full (bonus-included), matching _flagged_body_row/_exobio_progress_row. """
        prefix:str = "" if confirmed_signal else "?"
        value_min:int = exobiology.with_first_logged_bonus(slot["value_min"], was_footfalled)
        value_max:int = exobiology.with_first_logged_bonus(slot["value_max"], was_footfalled)
        value_str:str = _credits_range(value_min, value_max)
        if value_min != value_max:
            value_str = f"~{value_str}"
        return (f"{prefix}{slot['name']}", _sampling_distance_str(slot["genera"]), value_str)

    def _exobio_row_range(self, row:sqlite3.Row) -> tuple[int, int]:
        """ Exact once sampled; else narrowed to surviving Scan-time species predictions, not the full genus range. """
        if row["species"]:
            value:int = row["confirmed_value"] or 0
            return (value, value)

        genus:str = row["genus"] or ""
        candidates:list[sqlite3.Row] = [
            p for p in self.store.get_genus_predictions_for_body(row["body_id"]) if p["genus"] == genus and p["species"]
        ]

        if candidates:
            values:list[int] = [exobiology.estimate_confirmed_value(genus, c["species"]) or 0 for c in candidates]
            return (min(values), max(values))
        value_range:tuple[int, int]|None = exobiology.estimate_genus_range(genus)

        return value_range if value_range else (0, 0)

    def _join_species_names(self, genus:str, names:list[str]) -> str:
        """ first name kept in full, genus prefix stripped from the rest, then joined with slashes. """
        prefix:str = f"{genus} "
        joined:list[str] = [names[0]] + [n[len(prefix):] if n.startswith(prefix) else n for n in names[1:]]

        return str_truncate("/".join(joined), MAX_SPECIES_LABEL_CHARS)

    def _possible_species_label(self, body_pk:int, genus:str) -> str:
        """ Still-plausible species from the Scan-time prediction, confidence-sorted, or "genus sp." if none. """
        candidates:list[sqlite3.Row] = sorted(
            (p for p in self.store.get_genus_predictions_for_body(body_pk) if p["genus"] == genus and p["species"]),
            key=lambda p: -p["confidence"],
        )
        if not candidates:
            return f"{genus} sp."

        return self._join_species_names(genus, [c["species"] for c in candidates])

    def _exobio_progress_row(self, row:sqlite3.Row, was_footfalled:bool) -> tuple[str, str, str, str]:
        """ Genus placeholder becomes the species name (and value the confirmed value) once
        sampled. Value shown is Full (bonus-included) -- the base value counting toward ED's own
        progression is never shown in this compact panel, only in the history view. """
        genus:str = row["genus"] or "biological"
        name:str = row["species"] or self._possible_species_label(row["body_id"], genus)
        progress:str = f"{row['samples_taken']}/{SAMPLES_REQUIRED}"
        value_min, value_max = self._exobio_row_range(row)
        value_min = exobiology.with_first_logged_bonus(value_min, was_footfalled)
        value_max = exobiology.with_first_logged_bonus(value_max, was_footfalled)
        distance:str = _sampling_distance_str([genus])
        value_str:str = _credits_range(value_min, value_max)

        if value_min != value_max:
            value_str = f"~{value_str}"

        return (name, progress, distance, value_str)
