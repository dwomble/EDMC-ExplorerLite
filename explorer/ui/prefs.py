""" nb.* not th.*, matches EDMC settings dialog theming. """
import tkinter as tk
from tkinter import ttk, colorchooser, font as tkfont
from dataclasses import dataclass
from functools import partial

import myNotebook as nb # type: ignore
from ttkHyperlinkLabel import HyperlinkLabel # type: ignore
from config import config # type: ignore

from explorer.constants import (
    PLUGIN_NAME, VERSION, GH_OWNER, GH_PROJECT,
    CFG_SCAN_VALUE_THRESHOLD, DEFAULT_SCAN_VALUE_THRESHOLD,
    CFG_EXOBIO_VALUE_THRESHOLD, DEFAULT_EXOBIO_VALUE_THRESHOLD,
    CFG_OVERLAY_RADAR_ENABLED, CFG_OVERLAY_SUMMARY_ENABLED, CFG_DEV_MODE,
    CFG_VISIBLE_LINES, DEFAULT_VISIBLE_LINES,
    CFG_OVERLAY_RADAR_SIZE, DEFAULT_OVERLAY_RADAR_SIZE,
    CFG_OVERLAY_SUMMARY_TEXT_COLOR, DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR,
)

OVERLAYS_SECTION:str = "Overlays" # must match its title in SECTIONS below

GH_URL:str = f"https://github.com/{GH_OWNER}/{GH_PROJECT}"

@dataclass
class Pref:
    kind:str # 'threshold', 'bool', or 'color'
    key:str
    desc:str
    default:int|bool|str

SECTIONS:list[tuple[str, list[Pref]]] = [
    ("Thresholds", [
        Pref('threshold', CFG_SCAN_VALUE_THRESHOLD, "Flag scan/mapping value above (Cr):", DEFAULT_SCAN_VALUE_THRESHOLD),
        Pref('threshold', CFG_EXOBIO_VALUE_THRESHOLD, "Flag exobiology potential above (Cr):", DEFAULT_EXOBIO_VALUE_THRESHOLD),
        Pref('threshold', CFG_VISIBLE_LINES, "Visible lines before scrolling:", DEFAULT_VISIBLE_LINES),
    ]),
    (OVERLAYS_SECTION, [
        Pref('bool', CFG_OVERLAY_RADAR_ENABLED, "Show radar on overlay", True),
        Pref('bool', CFG_OVERLAY_SUMMARY_ENABLED, "Show system summary on overlay", True),
        Pref('threshold', CFG_OVERLAY_RADAR_SIZE, "Radar size (px):", DEFAULT_OVERLAY_RADAR_SIZE),
        Pref('color', CFG_OVERLAY_SUMMARY_TEXT_COLOR, "Overlay summary text colour:", DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR),
    ]),
    ("Debug", [
        Pref('bool', CFG_DEV_MODE, "Developer/debug logging", False),
    ]),
]
PREFS:list[Pref] = [p for _, section_prefs in SECTIONS for p in section_prefs] # save_prefs() iterates this flat

LABEL_GAP_PX:int = 16 # between a pref's own label and its control
GROUP_GAP_PX:int = 24 # between the left half and the right half
ROW_GAP_PX:int = 6 # vertical space between pref rows

_pref_vars:dict[str, tk.Variable] = {}

def _bold_font() -> tkfont.Font:
    default:tkfont.Font = tkfont.nametofont("TkDefaultFont")
    return tkfont.Font(family=default.actual("family"), size=default.actual("size"), weight="bold")

def _pick_color(parent:tk.Widget, var:tk.StringVar, btn:tk.Button) -> None:
    _, color = colorchooser.askcolor(var.get(), title="Overlay summary text colour", parent=parent)
    if color:
        var.set(color)
        btn.configure(text="Foreground", foreground=color)

def _place_pref(frame:nb.Frame, p:Pref, row:int, col:int, enabled:bool) -> None:
    """ col: 0 for the left half, 2 for the right half. """
    state:str = tk.NORMAL if enabled else tk.DISABLED
    left_pad:int = GROUP_GAP_PX if col == 2 else 0
    pady:tuple[int, int] = (0, ROW_GAP_PX)
    match p.kind:
        case 'threshold':
            _pref_vars[p.key] = tk.StringVar(value=str(config.get_int(p.key, default=p.default)))
            nb.Label(frame, text=p.desc).grid(row=row, column=col, sticky=tk.W, padx=(left_pad, LABEL_GAP_PX), pady=pady)
            nb.EntryMenu(frame, textvariable=_pref_vars[p.key], width=10, state=state).grid(row=row, column=col + 1, sticky=tk.W, pady=pady)

        case 'bool':
            _pref_vars[p.key] = tk.BooleanVar(value=config.get_bool(p.key, default=p.default))
            nb.Checkbutton(frame, text=p.desc, variable=_pref_vars[p.key], state=state).grid(
                row=row, column=col, columnspan=2, sticky=tk.W, padx=(left_pad, 0), pady=pady)

        case 'color':
            color:str = config.get_str(p.key, default=p.default)
            color_var:tk.StringVar = tk.StringVar(value=color)
            _pref_vars[p.key] = color_var
            nb.Label(frame, text=p.desc).grid(row=row, column=col, sticky=tk.W, padx=(left_pad, LABEL_GAP_PX), pady=pady)
            btn:tk.Button = tk.Button(frame, text="Foreground", foreground=color, background="#555555", state=state)
            btn.configure(command=partial(_pick_color, frame, color_var, btn))
            btn.grid(row=row, column=col + 1, sticky=tk.W, pady=pady)

def _build_section(frame:nb.Frame, section_prefs:list[Pref], row:int, enabled:bool = True) -> int:
    """ Flows prefs two-up, alternating left then right. """
    col:int = 0

    for p in section_prefs:
        _place_pref(frame, p, row, col, enabled)
        row, col = (row + 1, 0) if col == 2 else (row, 2)

    return row + 1 if col != 0 else row

def build_prefs(parent:tk.Widget, cmdr:str, is_beta:bool, overlay_available:bool = True) -> tk.Widget:
    global _pref_vars
    _pref_vars = {}

    frame:nb.Frame = nb.Frame(parent)
    frame.columnconfigure(3, weight=1) # only the trailing column stretches -- keeps halves close
    bold:tkfont.Font = _bold_font()

    row:int = 0
    nb.Label(frame, text=f"{PLUGIN_NAME} v{VERSION}", font=bold).grid(row=row, column=0, columnspan=3, sticky=tk.W)
    HyperlinkLabel(frame, text="GitHub", url=GH_URL, underline=True).grid(row=row, column=3, sticky=tk.E)
    row += 1
    ttk.Separator(frame).grid(row=row, column=0, columnspan=4, sticky=tk.EW, pady=6)
    row += 1

    for title, section_prefs in SECTIONS:
        nb.Label(frame, text=title, font=bold).grid(row=row, column=0, columnspan=4, sticky=tk.W, pady=(4, 2))
        row += 1
        enabled:bool = overlay_available or title != OVERLAYS_SECTION
        row = _build_section(frame, section_prefs, row, enabled)

    return frame

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
