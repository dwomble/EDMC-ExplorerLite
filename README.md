# EDMC-ExplorerLite

An unobtrusive, lightweight exploration and exobiology assistant for [EDMC](https://github.com/EDCD/EDMarketConnector).

<img width="478" height="47" alt="Screenshot 2026-08-16 215121" src="https://github.com/user-attachments/assets/92830698-5053-4837-85f4-17b48ed7cbc1" />

At every stage of exploring a system ExplorerLite tells you whether it's worth your time and what's worth doing next, in a clean, compact panel that gets out of the way when there's nothing to report. It's designed to be lightweight and self-contained with overlay support for single-screen/VR/heads-up operation.

## Key Features

- Clean, simple, theme-aware UI shows the information you need and nothing you don't.
- Honk heuristic flags whether a system is worth a full FSS pass, based on star type and body/signal counts.
- Flags bodies whose cartography (scan/mapping) value or exobiology potential clears your configured credit thresholds, including first-discovery/first-mapped bonus.
- Pre-DSS genus/species prediction: ranks likely biology from a body's atmosphere, temperature, gravity, and volcanism as soon as it's scanned
- Live per-species sampling progress once you're on the ground, including the first-logged bonus.
- Other species tagged with the compisition scanner will show up as waypoints in the radar so you can return to them.
- In-game overlay: a sample-tracking radar plus a glanceable system summary, so you rarely need to alt-tab to the panel.
- Per-commander history browser with running sold/pending totals for both cartography and exobiology.
- 👁/🙈 toggle minimizes the display when not exploring.

<img width="477" height="173" alt="Screenshot 2026-08-16 183627" src="https://github.com/user-attachments/assets/15b6d141-8385-47ee-ba5d-9474bd56aaa6" />

## Installation

Create a directory in your EDMC `plugins` folder called `EDMC-ExplorerLite`, download the latest release .zip file and extract it into that directory, then restart EDMC.

## Honk

The system line shows the known body count plus the next thing worth doing, e.g. `Deltius — 7 bodies — **DSS**`. `Honk` → `FSS` → `DSS` / `Sample` / `DSS + Sample` → `Done`. `FSS` (Full Spectrum Scan) stays until you've finished scanning the system bodies. `DSS` (Detailed Surface Scan) means a scanned body is worth mapping, either for its cargographic value or its biological value; `Sample` (Genetic Sampling) means a mapped body still needs its biology sampled; `DSS + Sample` means both are true somewhere in the system. `Done` covers both "nothing here was worth a full scan" and "genuinely nothing left to do."

## FSS

As bodies are scanned, any whose estimated cartography value clears your threshold are listed with type (`T HMC`, `WW`, `ELW`, `AW`, `GG`, etc. — `T` prefix for terraformable), distance, gravity, and approximate value.

## DSS

Bodies whose value exceeds a configurable threshold are recommended for DSS as are planets whose likely biologicals exceed a configurable threshold.

## Exobiology

When the FSS reports biological signals on a body, ExplorerLite indicates likely genera based on the body's atmosphere, temperature, gravity, volcanism, and nearby star type. Estimated genera are shown with a `?` prefix and a value range until confirmed. The DSS narrows this to the genera actually present and the first genetic sample per genus locks in the exact species (if not already determined) and variant.

Per-species genetic sampling progress (`N/M scanned`) is shown live while you're on the body, along with the minimum distance required between samples for that genus. Values shown always include the first-discovery/first-logged bonus you'd actually be paid — not just the base value that only matters for in-game session-progression math.

<img width="406" height="177" alt="Screenshot 2026-08-16 215440" src="https://github.com/user-attachments/assets/cd1d5511-7c9f-4243-9878-236ebaba80fa" />


## Overlay

Requires the [modern overlay](https://github.com/SweetJonnySauce/EDMCModernOverlay), the legacy `EDMCOverlay`/`edmcoverlay2` plugins aren't supported. Without it, ExplorerLite still works fully — the overlay is a heads-up convenience, not a requirement. The panel's 👁/🙈 header toggle hides both overlay elements too, alongside the panel's own content. Both also hide automatically whenever they'd just be in the way — docked, on-foot inside a station, with any ship/on-foot panel (galaxy map, system map, station services, etc.) open, etc..

Two independently toggleable overlay elements:

- **System summary** — mirrors the panel's own header and flagged-body list (same columns: distance, gravity, type, value), capped to a handful of lines (with a "+N more" overflow) so it stays glanceable. The body you're currently standing on gets its own indented species-progress detail underneath. Text colour is configurable. Background, border and position are configurable via Modern Overlay's overlay controller.

- **Radar** — centered on you, shows distance rings, a highlighted ring at the current genus's minimum sample distance, a marker for each logged sample (filled = in range, hollow = out of range), and a hollow triangle for any comp. scanner-tagged waypoint, colored by variant. Rotates with your heading. Radar size is configurable.

<img width="200" height="196" alt="Screenshot 2026-08-16 182145" src="https://github.com/user-attachments/assets/6dca3cd4-35f2-4770-8d06-a8da67d768fd" />

## Panel header

The top row of the panel is always visible — the plugin name on the left, your pending cartography and exobiology credits in the middle, and two icon buttons on the right (all four have tooltips):

- 🕓 opens the History browser (below).
- 🙈/👁 shows or hides everything below the header as well as the overlays. Data collection continues but this declutters the EDMC window. Your choice is remembered across restarts.

## History

Click 🕓 on the panel to open a System → Body → Species browser (per Cmdr), showing status, date, and both estimated and actual value for cartography (`Cart. Est.`/`Cart. Actual`) and exobiology (`Exo. Base`/`Exo. Full`). A running totals line at the top shows sold vs. still-pending credits for both categories, alongside an "Unsold only" checkbox (on by default) and a time-range dropdown (All time/Last day/Last week/Last month) so a long career's history stays manageable — both choices are remembered across sessions, as is window size/position. The underlying query is also capped to the 1,000 most recently visited systems.

Actual sold values always come straight from the ED journal — ground truth, never a formula. Estimates exist purely to flag what's worth your time before you sell.

<img width="1030" height="397" alt="Screenshot 2026-08-16 214935" src="https://github.com/user-attachments/assets/db8f58ab-8669-49bd-8f74-56c2277c63bc" />

## Settings

The following settings are configurable from the EDMC preferences panel:

- **Thresholds** — minimum cartography (scan/mapping) value, minimum exobiology species value, panel lines before scrolling
- **Overlays** — radar on/off, system summary on/off, radar size, overlay summary text colour (greyed out entirely if no overlay backend is installed)
- **Debug** — developer/debug logging

## Persistence

All data and progress is stored locally in a per-install database segmented per commander. The only network call ExplorerLite makes is its own update check against this repo's GitHub releases.

## Requirements

- A recent version of EDMC (needs `plugin_app`/`dashboard_entry` support).
- Optional: [EDMCModernOverlay](https://github.com/SweetJonnySauce/EDMCModernOverlay) for the radar and system-summary overlays.

## Acknowledgements

- Cartography value constants cross-checked against two independent community sources, including the Frontier forums' "Exploration value formulae" thread.
- Exobiology species value/distance data sourced from the Elite Dangerous Fandom wiki's "Exobiology Sample Values and Details" page, cross-checked against [njthomson/SrvSurvey](https://github.com/njthomson/SrvSurvey)'s organic-scanning reference.
- Genus spawn-condition data independently transcribed from public sources, cross-checked against [Silarn/EDMC-BioScan](https://github.com/Silarn/EDMC-BioScan) (GPLv2) and ed-dsn.net's community temperature-band data.
- Codex-tag overlay colors cross-checked against EDMC-BioScan's own variant color names.

## Suggestions

Please let me know if you have any suggestions or find any bugs by submitting an [issue](https://github.com/dwomble/EDMC-NeutronDancer/issues), and if you like ExplorerLite I don't need a coffee, I live in Seattle so I'm plenty caffeinated already, but please give it a ⭐.

Fly dangerous! o7
