""" nb.* not th.*, matches EDMC settings dialog theming. """
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, font as tkfont
from dataclasses import dataclass
from functools import partial
from typing import Callable

import myNotebook as nb # type: ignore
from ttkHyperlinkLabel import HyperlinkLabel # type: ignore
from config import config # type: ignore

import explorer.utils.th as th
from explorer.valuation import mining

from explorer.constants import (
    PLUGIN_NAME, GH_OWNER, GH_PROJECT,
    CFG_SCAN_VALUE_THRESHOLD, DEFAULT_SCAN_VALUE_THRESHOLD,
    CFG_EXOBIO_VALUE_THRESHOLD, DEFAULT_EXOBIO_VALUE_THRESHOLD,
    CFG_OVERLAY_RADAR_ENABLED, CFG_OVERLAY_SUMMARY_ENABLED, CFG_DEV_MODE,
    CFG_VISIBLE_LINES, DEFAULT_VISIBLE_LINES,
    CFG_OVERLAY_RADAR_SIZE, DEFAULT_OVERLAY_RADAR_SIZE, CFG_OVERLAY_RADAR_CIRCLES, CFG_OVERLAY_RADAR_SWEEP,
    CFG_OVERLAY_SUMMARY_TEXT_COLOR, DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR,
    CFG_BODY_SORT, DEFAULT_BODY_SORT, BODY_SORTS, CFG_MINING_ENABLED, CFG_MINING_MIN_COMMODITY, CFG_MINING_MIN_MATERIAL, CFG_MINING_COMMODITIES, CFG_MINING_MATERIALS,
)

OVERLAYS_SECTION:str = "Overlays" # must match its title in SECTIONS below
DATA_SECTION_TITLE:str = "Data"

GH_URL:str = f"https://github.com/{GH_OWNER}/{GH_PROJECT}"

@dataclass
class Pref:
    kind:str # 'threshold', 'bool', 'color', 'choice' or 'text'
    key:str
    desc:str
    default:int|bool|str
    tooltip:str|None = None
    options:tuple[str, ...] = ()

SECTIONS:list[tuple[str, list[Pref]]] = [
    ("Thresholds", [
        Pref('threshold', CFG_SCAN_VALUE_THRESHOLD, "Minimum DSS value", DEFAULT_SCAN_VALUE_THRESHOLD, "Minimum value of a body scan to be shown. Bodies below this value will be ignored."),
        Pref('threshold', CFG_EXOBIO_VALUE_THRESHOLD, "Minimum exobiology value", DEFAULT_EXOBIO_VALUE_THRESHOLD, "Minimum value of exobiology scans to be shown. Bodies below this value will be ignored."),
        Pref('threshold', CFG_VISIBLE_LINES, "Maximum visible lines", DEFAULT_VISIBLE_LINES, "Number of lines to display before enabling scrolling."),
    ]),
    ("Display", [
        Pref('choice', CFG_BODY_SORT, "Body sort order", DEFAULT_BODY_SORT,
             "How listed bodies are ordered: by name (A 2 before A 10), highest value first, or nearest the arrival star first.", BODY_SORTS),
    ]),
    ("Mining watch list", [
        Pref('bool', CFG_MINING_ENABLED, "Show mining rows", True, "Show watch-list commodities and materials under landable bodies."),
        Pref('text', CFG_MINING_COMMODITIES, "Commodities", "",
             "Comma-separated surface mining commodities (e.g. Platinum, Olivine). Landable bodies likely to have one or more get a mining row, with the survey odds."),
        Pref('text', CFG_MINING_MATERIALS, "Materials", "",
             "Comma-separated materials (e.g. Antimony, Polonium). Landable bodies whose scan lists one or more get a mining row, with the exact percentage."),
        Pref('threshold', CFG_MINING_MIN_COMMODITY, "Minimum commodity %", 0, "Hide commodities whose survey odds on a body are below this percentage."),
        Pref('threshold', CFG_MINING_MIN_MATERIAL, "Minimum material %", 0, "Hide materials whose scanned percentage on a body is below this value."),
    ]),
    (OVERLAYS_SECTION, [
        Pref('bool', CFG_OVERLAY_RADAR_ENABLED, "Show radar overlay", True, "When near a body with cartography potential, show a radar overlay of scans and waypoints."),
        Pref('bool', CFG_OVERLAY_SUMMARY_ENABLED, "Show summary overlay", True, "Display a summary of cartography and exobiology data."),
        Pref('threshold', CFG_OVERLAY_RADAR_SIZE, "Radar size", DEFAULT_OVERLAY_RADAR_SIZE, "Pixel radius of the radar overlay."),
        Pref('bool', CFG_OVERLAY_RADAR_CIRCLES, "Sample-focused radar", True, "Show scan distance as circle around each sample (scan or waypoint) rather than\nthe default Commander-focused single minimum distance circle around the current location (requires circle-capable overlay)."),
        Pref('bool', CFG_OVERLAY_RADAR_SWEEP, "Radar sweep line", False, "Animate a rotating sweep line on the radar (redrawn about 15 times a second)."),
        Pref('color', CFG_OVERLAY_SUMMARY_TEXT_COLOR, "Summary overlay text colour", DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR, "Colour of the text displayed in the summary overlay."),
    ]),
    ("Debug", [
        Pref('bool', CFG_DEV_MODE, "Developer/debug logging", False),
    ]),
]
PREFS:list[Pref] = [p for _, section_prefs in SECTIONS for p in section_prefs] # save_prefs() iterates this flat

LABEL_GAP_PX:int = 16 # between a pref's own label and its control
GROUP_GAP_PX:int = 24 # between the left half and the right half
ROW_GAP_PX:int = 6 # vertical space between pref rows
PAD_PX:int = 10 # matches the padding BGS-Tally and NeutronDancer give their settings tabs
DANGER_COLOR:str = "#ee0000" # flags an irreversible action, e.g. Clear unsold data

_pref_vars:dict[str, tk.Variable] = {}

def _place_pref(frame:nb.Frame, p:Pref, row:int, col:int, enabled:bool) -> None:
    """ col: 0 for the left half, 2 for the right half. """

    def _pick_color(parent:tk.Widget, var:tk.StringVar, btn:tk.Button) -> None:
        _, color = colorchooser.askcolor(var.get(), title="Overlay summary text colour", parent=parent)
        if color:
            var.set(color)
            btn.configure(text="Foreground", foreground=color)

    state:str = tk.NORMAL if enabled else tk.DISABLED
    left_pad:int = GROUP_GAP_PX if col == 2 else 0
    pady:tuple[int, int] = (0, ROW_GAP_PX)
    match p.kind:
        case 'threshold':
            _pref_vars[p.key] = tk.StringVar(value=str(config.get_int(p.key, default=p.default)))
            lbl:nb.Label = nb.Label(frame, text=p.desc)
            lbl.grid(row=row, column=col, sticky=tk.W, padx=(left_pad, LABEL_GAP_PX), pady=pady)
            mnu:nb.EntryMenu = nb.EntryMenu(frame, textvariable=_pref_vars[p.key], width=10, state=state)
            mnu.grid(row=row, column=col + 1, sticky=tk.W, pady=pady)
            if p.tooltip:
                th.Tooltip(lbl, p.tooltip)
                th.Tooltip(mnu, p.tooltip)

        case 'bool':
            _pref_vars[p.key] = tk.BooleanVar(value=config.get_bool(p.key, default=p.default))
            cb:nb.Checkbutton = nb.Checkbutton(frame, text=p.desc, variable=_pref_vars[p.key], state=state)
            cb.grid(row=row, column=col, columnspan=2, sticky=tk.W, padx=(left_pad, 0), pady=pady)
            if p.tooltip:
                th.Tooltip(cb, p.tooltip)

        case 'choice':
            _pref_vars[p.key] = tk.StringVar(value=config.get_str(p.key, default=p.default))
            lbl:nb.Label = nb.Label(frame, text=p.desc)
            lbl.grid(row=row, column=col, sticky=tk.W, padx=(left_pad, LABEL_GAP_PX), pady=pady)
            opt:nb.OptionMenu = nb.OptionMenu(frame, _pref_vars[p.key], _pref_vars[p.key].get(), *p.options)
            opt.configure(state=state)
            opt.grid(row=row, column=col + 1, sticky=tk.W, pady=pady)
            if p.tooltip:
                th.Tooltip(lbl, p.tooltip)
                th.Tooltip(opt, p.tooltip)

        case 'text':
            _pref_vars[p.key] = tk.StringVar(value=config.get_str(p.key, default=p.default))
            lbl:nb.Label = nb.Label(frame, text=p.desc)
            lbl.grid(row=row, column=col, sticky=tk.W, padx=(left_pad, LABEL_GAP_PX), pady=pady)
            ent:nb.EntryMenu = nb.EntryMenu(frame, textvariable=_pref_vars[p.key], width=30, state=state)
            ent.grid(row=row, column=col + 1, sticky=tk.W, pady=pady)
            if p.tooltip:
                th.Tooltip(lbl, p.tooltip)
                th.Tooltip(ent, p.tooltip)

        case 'color':
            color:str = config.get_str(p.key, default=p.default)
            color_var:tk.StringVar = tk.StringVar(value=color)
            _pref_vars[p.key] = color_var
            lbl:nb.Label = nb.Label(frame, text=p.desc)
            lbl.grid(row=row, column=col, sticky=tk.W, padx=(left_pad, LABEL_GAP_PX), pady=pady)
            btn:tk.Button = tk.Button(frame, text="Foreground", foreground=color, background="#555555", state=state)
            btn.configure(command=partial(_pick_color, frame, color_var, btn))
            btn.grid(row=row, column=col + 1, sticky=tk.W, pady=pady)
            if p.tooltip:
                th.Tooltip(lbl, p.tooltip)
                th.Tooltip(btn, p.tooltip)

def _on_clear_unsold_data(parent:tk.Widget, cmdr:str, clear_unsold_data:Callable[[str], str]|None) -> None:
    if clear_unsold_data is None:
        return
    confirmed:bool = messagebox.askyesno(
        "Clear unsold data",
        "Mark all pending cartography and exobiology data as lost?\nThis cannot be undone.",
        parent=parent,
    )
    if not confirmed:
        return
    messagebox.showinfo("Clear unsold data", clear_unsold_data(cmdr), parent=parent)

def _build_section(frame:nb.Frame, section_prefs:list[Pref], row:int, enabled:bool = True) -> int:
    """ Flows prefs two-up, alternating left then right. """
    col:int = 0

    for p in section_prefs:
        _place_pref(frame, p, row, col, enabled)
        row, col = (row + 1, 0) if col == 2 else (row, 2)

    return row + 1 if col != 0 else row

def build_prefs(parent:tk.Widget, cmdr:str, is_beta:bool, overlay_available:bool = True, version:str = "0.0.0",
                clear_unsold_data:Callable[[str], str]|None = None) -> tk.Widget:
    global _pref_vars
    _pref_vars = {}

    outer:nb.Frame = nb.Frame(parent)
    outer.columnconfigure(0, weight=1)
    frame:nb.Frame = nb.Frame(outer)
    frame.grid(row=0, column=0, padx=PAD_PX, pady=PAD_PX, sticky=tk.NSEW)
    frame.columnconfigure(3, weight=1) # only the trailing column stretches -- keeps halves close
    default:tkfont.Font = tkfont.nametofont("TkDefaultFont")
    bold:tkfont.Font = tkfont.Font(family=default.actual("family"), size=default.actual("size"), weight="bold")

    row:int = 0; col:int = 0
    nb.Label(frame, text=f"{PLUGIN_NAME} v{version}", font=bold).grid(row=row, column=0, columnspan=3, sticky=tk.W)
    HyperlinkLabel(frame, text="GitHub", url=GH_URL, underline=True).grid(row=row, column=3, sticky=tk.E)
    row += 1
    ttk.Separator(frame).grid(row=row, column=col, columnspan=4, sticky=tk.EW, pady=6)
    row += 1

    for title, section_prefs in SECTIONS:
        nb.Label(frame, text=title, font=bold).grid(row=row, column=0, columnspan=4, sticky=tk.W, pady=(4, 2))
        row += 1
        enabled:bool = overlay_available or title != OVERLAYS_SECTION
        row = _build_section(frame, section_prefs, row, enabled)

    nb.Label(frame, text=DATA_SECTION_TITLE, font=bold).grid(row=row, column=col, columnspan=4, sticky=tk.W, pady=(4, 2))
    row += 1; col = 0
    lbl:nb.Label = nb.Label(frame, text="Clear unsold data")
    lbl.grid(row=row, column=0, sticky=tk.W, pady=(0, ROW_GAP_PX))
    th.Tooltip(lbl, "Danger! This is an irreversible action! It will mark all pending cartography and exobiology data as lost,\nas if the commander died without EDMC running. Use only if you are sure you want to do this.")
    col += 1
    btn:tk.Button = tk.Button(frame, text="Delete", background=DANGER_COLOR, foreground="white",
                               activebackground=DANGER_COLOR, command=partial(_on_clear_unsold_data, frame, cmdr, clear_unsold_data),
    )
    btn.grid(row=row, column=col, rowspan=3, sticky=tk.W, pady=(0, ROW_GAP_PX))
    th.Tooltip(btn, "Danger! This is an irreversible action! It will mark all pending cartography and exobiology data as lost,\nas if the commander died without EDMC running. Use only if you are sure you want to do this.")

    return outer

def _warn_unknown_names() -> None:
    """ Typos are kept (the survey data may gain names) but flagged with the nearest known name. """
    lines:list[str] = []
    for key, known in ((CFG_MINING_COMMODITIES, mining.known_commodities()), (CFG_MINING_MATERIALS, list(mining.MATERIALS))):
        var = _pref_vars.get(key)
        if var is None: continue

        lines += [f"{n} - did you mean {s}?" if s else f"{n} - not recognised" for n, s in mining.unknown_names(var.get(), known)]

    if lines: messagebox.showwarning(PLUGIN_NAME, "Unrecognised mining watch-list names:\n\n" + "\n".join(lines))

def save_prefs(cmdr:str, is_beta:bool) -> None:
    for p in PREFS:
        var = _pref_vars.get(p.key)
        if var is None:
            continue

        match p.kind:
            case 'threshold':
                config.set(p.key, int(var.get()) if var.get().isdigit() else p.default)
            case _:
                config.set(p.key, var.get())

    _warn_unknown_names()
