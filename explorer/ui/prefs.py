"""
Settings pane: the two credit thresholds, overlay toggles, dev-mode flag. Uses myNotebook
(nb.*) widgets, matching how EDMC's own settings dialog themes plugin_prefs frames -- th.*
widgets are reserved for the main panel and (later) the history popup.
"""
import tkinter as tk

import myNotebook as nb # type: ignore
from config import config # type: ignore

from explorer.constants import (
    CFG_SCAN_VALUE_THRESHOLD, DEFAULT_SCAN_VALUE_THRESHOLD,
    CFG_EXOBIO_VALUE_THRESHOLD, DEFAULT_EXOBIO_VALUE_THRESHOLD,
    CFG_OVERLAY_ENABLED, CFG_OVERLAY_RADAR_ENABLED, CFG_DEV_MODE,
)

_scan_threshold_var:tk.StringVar|None = None
_exobio_threshold_var:tk.StringVar|None = None
_overlay_enabled_var:tk.BooleanVar|None = None
_overlay_radar_enabled_var:tk.BooleanVar|None = None
_dev_mode_var:tk.BooleanVar|None = None

def build_prefs(parent:tk.Widget, cmdr:str, is_beta:bool) -> tk.Widget:
    global _scan_threshold_var, _exobio_threshold_var, _overlay_enabled_var, _overlay_radar_enabled_var, _dev_mode_var

    frame = nb.Frame(parent)
    frame.columnconfigure(1, weight=1)

    _scan_threshold_var = tk.StringVar(value=str(config.get_int(CFG_SCAN_VALUE_THRESHOLD, default=DEFAULT_SCAN_VALUE_THRESHOLD)))
    _exobio_threshold_var = tk.StringVar(value=str(config.get_int(CFG_EXOBIO_VALUE_THRESHOLD, default=DEFAULT_EXOBIO_VALUE_THRESHOLD)))
    _overlay_enabled_var = tk.BooleanVar(value=config.get_bool(CFG_OVERLAY_ENABLED, default=True))
    _overlay_radar_enabled_var = tk.BooleanVar(value=config.get_bool(CFG_OVERLAY_RADAR_ENABLED, default=True))
    _dev_mode_var = tk.BooleanVar(value=config.get_bool(CFG_DEV_MODE, default=False))

    row = 0
    nb.Label(frame, text="Flag a body's scan/mapping value above (Cr):").grid(row=row, column=0, sticky="w")
    nb.EntryMenu(frame, textvariable=_scan_threshold_var, width=12).grid(row=row, column=1, sticky="e")

    row += 1
    nb.Label(frame, text="Flag exobiology potential above (Cr):").grid(row=row, column=0, sticky="w")
    nb.EntryMenu(frame, textvariable=_exobio_threshold_var, width=12).grid(row=row, column=1, sticky="e")

    row += 1
    nb.Checkbutton(frame, text="Enable overlay", variable=_overlay_enabled_var).grid(row=row, column=0, columnspan=2, sticky="w")

    row += 1
    nb.Checkbutton(frame, text="Show radar on overlay", variable=_overlay_radar_enabled_var).grid(row=row, column=0, columnspan=2, sticky="w")

    row += 1
    nb.Checkbutton(frame, text="Developer/debug logging", variable=_dev_mode_var).grid(row=row, column=0, columnspan=2, sticky="w")

    return frame

def _set_int(key:str, raw:str, default:int) -> None:
    try:
        config.set(key, int(raw))
    except ValueError:
        config.set(key, default)

def save_prefs(cmdr:str, is_beta:bool) -> None:
    if _scan_threshold_var is not None:
        _set_int(CFG_SCAN_VALUE_THRESHOLD, _scan_threshold_var.get(), DEFAULT_SCAN_VALUE_THRESHOLD)
    if _exobio_threshold_var is not None:
        _set_int(CFG_EXOBIO_VALUE_THRESHOLD, _exobio_threshold_var.get(), DEFAULT_EXOBIO_VALUE_THRESHOLD)
    if _overlay_enabled_var is not None:
        config.set(CFG_OVERLAY_ENABLED, _overlay_enabled_var.get())
    if _overlay_radar_enabled_var is not None:
        config.set(CFG_OVERLAY_RADAR_ENABLED, _overlay_radar_enabled_var.get())
    if _dev_mode_var is not None:
        config.set(CFG_DEV_MODE, _dev_mode_var.get())
