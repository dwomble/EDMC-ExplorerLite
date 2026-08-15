"""
Settings pane: the two credit thresholds, overlay toggles, dev-mode flag. Uses myNotebook
(nb.*) widgets, matching how EDMC's own settings dialog themes plugin_prefs frames -- th.*
widgets are reserved for the main panel and the history popup.
"""
import tkinter as tk
from dataclasses import dataclass

import myNotebook as nb # type: ignore
from config import config # type: ignore

from explorer.constants import (
    CFG_SCAN_VALUE_THRESHOLD, DEFAULT_SCAN_VALUE_THRESHOLD,
    CFG_EXOBIO_VALUE_THRESHOLD, DEFAULT_EXOBIO_VALUE_THRESHOLD,
    CFG_OVERLAY_ENABLED, CFG_OVERLAY_RADAR_ENABLED, CFG_DEV_MODE,
    CFG_VISIBLE_LINES, DEFAULT_VISIBLE_LINES,
    CFG_OVERLAY_RADAR_SIZE, DEFAULT_OVERLAY_RADAR_SIZE,
)

@dataclass
class Pref:
    kind:str # 'threshold' or 'bool'
    key:str
    desc:str
    default:int|bool

PREFS = [
    Pref('threshold', CFG_SCAN_VALUE_THRESHOLD, "Flag a body's scan/mapping value above (Cr):", DEFAULT_SCAN_VALUE_THRESHOLD),
    Pref('threshold', CFG_EXOBIO_VALUE_THRESHOLD, "Flag exobiology potential above (Cr):", DEFAULT_EXOBIO_VALUE_THRESHOLD),
    Pref('threshold', CFG_VISIBLE_LINES, "Visible lines before scrolling:", DEFAULT_VISIBLE_LINES),
    Pref('bool', CFG_OVERLAY_ENABLED, "Enable overlay", True),
    Pref('bool', CFG_OVERLAY_RADAR_ENABLED, "Show radar on overlay", True),
    Pref('threshold', CFG_OVERLAY_RADAR_SIZE, "Radar size (px):", DEFAULT_OVERLAY_RADAR_SIZE),
    Pref('bool', CFG_DEV_MODE, "Developer/debug logging", False),
]

_pref_vars:dict[str, tk.Variable] = {}

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
