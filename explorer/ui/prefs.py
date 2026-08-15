"""
Settings pane: the two credit thresholds, overlay toggles, dev-mode flag. Uses myNotebook
(nb.*) widgets, matching how EDMC's own settings dialog themes plugin_prefs frames -- th.*
widgets are reserved for the main panel and the history popup.
"""
import tkinter as tk
from tkinter import colorchooser
from dataclasses import dataclass
from functools import partial

import myNotebook as nb # type: ignore
from config import config # type: ignore

from explorer.constants import (
    CFG_SCAN_VALUE_THRESHOLD, DEFAULT_SCAN_VALUE_THRESHOLD,
    CFG_EXOBIO_VALUE_THRESHOLD, DEFAULT_EXOBIO_VALUE_THRESHOLD,
    CFG_OVERLAY_ENABLED, CFG_OVERLAY_RADAR_ENABLED, CFG_OVERLAY_SUMMARY_ENABLED, CFG_DEV_MODE,
    CFG_VISIBLE_LINES, DEFAULT_VISIBLE_LINES,
    CFG_OVERLAY_RADAR_SIZE, DEFAULT_OVERLAY_RADAR_SIZE,
    CFG_OVERLAY_SUMMARY_TEXT_COLOR, DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR,
)

@dataclass
class Pref:
    kind:str # 'threshold', 'bool', or 'color'
    key:str
    desc:str
    default:int|bool|str

PREFS = [
    Pref('threshold', CFG_SCAN_VALUE_THRESHOLD, "Flag a body's scan/mapping value above (Cr):", DEFAULT_SCAN_VALUE_THRESHOLD),
    Pref('threshold', CFG_EXOBIO_VALUE_THRESHOLD, "Flag exobiology potential above (Cr):", DEFAULT_EXOBIO_VALUE_THRESHOLD),
    Pref('threshold', CFG_VISIBLE_LINES, "Visible lines before scrolling:", DEFAULT_VISIBLE_LINES),
    Pref('bool', CFG_OVERLAY_ENABLED, "Enable overlay", True),
    Pref('bool', CFG_OVERLAY_RADAR_ENABLED, "Show radar on overlay", True),
    Pref('bool', CFG_OVERLAY_SUMMARY_ENABLED, "Show system summary on overlay", True),
    Pref('threshold', CFG_OVERLAY_RADAR_SIZE, "Radar size (px):", DEFAULT_OVERLAY_RADAR_SIZE),
    Pref('color', CFG_OVERLAY_SUMMARY_TEXT_COLOR, "Overlay summary text colour:", DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR),
    Pref('bool', CFG_DEV_MODE, "Developer/debug logging", False),
]

_pref_vars:dict[str, tk.Variable] = {}

def _pick_color(parent:tk.Widget, var:tk.StringVar, btn:tk.Button) -> None:
    _, color = colorchooser.askcolor(var.get(), title="Overlay summary text colour", parent=parent)
    if color:
        var.set(color)
        btn.configure(text=color, foreground=color)

def build_prefs(parent:tk.Widget, cmdr:str, is_beta:bool) -> tk.Widget:
    global _pref_vars
    _pref_vars = {}

    frame:nb.Frame = nb.Frame(parent)
    frame.columnconfigure(1, weight=1)

    row:int = 0
    for p in PREFS:
        match p.kind:
            case 'threshold':
                _pref_vars[p.key] = tk.StringVar(value=str(config.get_int(p.key, default=p.default)))
                nb.Label(frame, text=p.desc).grid(row=row, column=0, sticky=tk.W)
                nb.EntryMenu(frame, textvariable=_pref_vars[p.key], width=12).grid(row=row, column=1, sticky=tk.E)
            case 'bool':
                _pref_vars[p.key] = tk.BooleanVar(value=config.get_bool(p.key, default=p.default))
                nb.Checkbutton(frame, text=p.desc, variable=_pref_vars[p.key]).grid(row=row, column=0, columnspan=2, sticky=tk.W)
            case 'color':
                color:str = config.get_str(p.key, default=p.default)
                color_var:tk.StringVar = tk.StringVar(value=color)
                _pref_vars[p.key] = color_var
                nb.Label(frame, text=p.desc).grid(row=row, column=0, sticky=tk.W)
                btn:tk.Button = tk.Button(frame, text=color, foreground=color, background="#555555")
                btn.configure(command=partial(_pick_color, frame, color_var, btn))
                btn.grid(row=row, column=1, sticky=tk.E)
        row += 1

    return frame

def save_prefs(cmdr:str, is_beta:bool) -> None:
    for p in PREFS:
        var = _pref_vars.get(p.key)
        if var is None:
            continue
        match p.kind:
            case 'threshold':
                config.set(p.key, int(var.get()) if var.get().isdigit() else p.default)
            case 'bool':
                config.set(p.key, var.get())
            case 'color':
                config.set(p.key, var.get())
