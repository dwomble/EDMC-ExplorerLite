# EDMC-ExplorerLite

A lightweight exploration + exobiology assistant for [EDMC](https://github.com/EDCD/EDMarketConnector), built on [EDMC-PluginLib](https://github.com/dwomble/EDMC-PluginLib).

Tells you, at each stage of exploring a system, whether it's worth your time and what's worth scanning — without cluttering the EDMC window or requiring network access.

## What it does

- **Honk** (`FSSDiscoveryScan`): a rough, offline heuristic for whether a full spectrum scan looks worthwhile.
- **FSS**: flags bodies whose estimated scan/mapping value, or exobiology potential, clears your configured credit thresholds.
- **On-body exobiology**: shows which species need scanning and per-species sample progress; an overlay radar shows sample positions, the required minimum distance for the active genus, and a heading tick.
- **Tracking**: actual (from `SellExplorationData`/`SellOrganicData` — ground truth) and estimated cartography/exobiology value, per Cmdr, browsable via the "History" popup.

## Install

Copy this directory into your EDMC `plugins` folder (rename the folder to `EDMC-ExplorerLite` if it isn't already).

## Overlay

Supports the modern `overlay_plugin.overlay_api` backend only (not the legacy `EDMCOverlay` plugin). Install a compatible modern overlay plugin if you want the radar; the rest of the plugin works fully offline without it.

## Settings

Two credit thresholds (scan/mapping value, exobiology potential), overlay on/off, radar on/off, and a dev-mode logging flag — all in EDMC's plugin settings pane.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/ -v
```

`explorer/utils/` and `tests/` are vendored from EDMC-PluginLib (no package/submodule mechanism exists there yet — see that project's own README for the copy-in convention). `utils/` is nested under `explorer/` rather than sitting at the plugin root, specifically to avoid colliding with any other installed plugin that also vendors this library — EDMC loads every plugin into one process with a shared `sys.path`, and two bare top-level `utils` packages from different plugins would otherwise silently collide via `sys.modules`.
