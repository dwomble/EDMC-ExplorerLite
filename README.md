# EDMC-ExplorerLite

A lightweight exploration and exobiology assistant for [EDMC](https://github.com/EDCD/EDMarketConnector).

At every stage of exploring a system — Discovery Scan (Honk), Full Spectrum Scan (FSS), Detailed Surface Scan (DSS), on-foot (genetic) sampling — ExplorerLite tells you whether it's worth your time and what's worth doing next, in a clean, compact panel that gets out of the way when there's nothing to report. It's designed to be lightweight and self-contained with overlay support for single-screen/VR/heads-up operation.

## Key Features

- Honk heuristic flags whether a system is worth a full FSS pass, based on body/signal counts (with an automatic override for neutron stars, white dwarfs, and black holes).
- Flags bodies whose cartography (scan/mapping) value or exobiology potential clears your configured credit thresholds, including first-discovery/first-mapped bonus.
- Pre-DSS genus/species prediction: ranks likely biology from a body's atmosphere, temperature, gravity, and volcanism as soon as it's scanned — no need to land blind.
- Live per-species sampling progress once you're on the ground, including the first-logged bonus.
- In-game overlay: a sample-tracking radar plus a glanceable system summary, so you rarely need to alt-tab to the panel.
- Per-commander history browser with running sold/pending totals for both cartography and exobiology.
- A show/hide toggle minimizes the display when not exploring.

## Installation

Create a directory into your EDMC `plugins` folder called `EDMC-ExplorerLite`, download the latest release .zip file and extract it into that directory, then restart EDMC.

## Honk

The system line always shows the single next thing worth doing: `Honk` → `FSS` → `DSS` / `Sample` / `DSS + Sample` → `Done`. `FSS` stays up for the whole scan pass, even once a body is already flagged — it only moves on once the FSS is actually complete. `DSS` means a scanned body is worth mapping; `Sample` means a mapped body still needs its biology sampled; `DSS + Sample` means both are true somewhere in the system. `Done` covers both "nothing here was worth a full scan" and "genuinely nothing left to do."

## FSS

As bodies are scanned, any whose estimated cartography value clears your threshold are listed with distance, gravity, type (`T HMC`, `WW`, `ELW`, `AW`, `GG`, etc. — `T` prefix for terraformable), and approximate value.

## DSS

Bodies whose value exceeds a configurable threshold are recommended for DSS as are planets whose likely biologicals exceed a configurable threshold.

## Exobiology

When the FSS reports biological signals on a body, ExplorerLite indicates likely genera based on the body's atmosphere, temperature, gravity, volcanism, and nearby star type. Estimated genera are shown with a `?` prefix and a value range until confirmed. The DSS narrows this to the genera actually present and the first genetic sample per genus locks in the exact species and variant.

Per-species genetic sampling progress (`N/M scanned`) is shown live while you're on the body, along with the minimum walking distance required between samples for that genus. Values shown always include the first-discovery/first-logged bonus you'd actually be paid — not just the base value that only matters for in-game session-progression math.

## Overlay

Requires the [modern overlay](https://github.com/SweetJonnySauce/EDMCModernOverlay), the legacy `EDMCOverlay`/`edmcoverlay2` plugins aren't supported. Without it, ExplorerLite still works fully — the overlay is a heads-up convenience, not a requirement. The panel's 👁/🙈 header toggle hides both overlay elements too, alongside the panel's own content.

Two independently toggleable overlay elements:

- **System summary** — mirrors the panel's own header and flagged-body list (same columns: distance, gravity, type, value), capped to a handful of lines (with a "+N more" overflow) so it stays glanceable. The body you're currently standing on gets its own indented species-progress detail underneath. Text colour is configurable. Background, border and position are configurable via Modern Overlay's overlay controller.

- **Radar** — centered on you, shows distance rings, a highlighted ring at the current genus's minimum sample distance, a marker for each logged sample (filled = in range, hollow = out of range), and a hollow triangle for any codex-tagged waypoint, colored by variant. Rotates with your heading. Radar size is configurable.

## Panel header

The top row of the panel is always visible — the plugin name on the left, your pending cartography and exobiology credits in the middle, and two icon buttons on the right (all four have tooltips):

- 🕓 opens the History browser (below).
- 🙈/👁 shows or hides everything below the header as well as the overlays. Data collection continues but this declutters the EDMC window. Your choice is remembered across restarts.

## History

Click 🕓 on the panel to open a System → Body → Species browser (per Cmdr), showing status, date, and both estimated and actual value for cartography (`Cart. Est.`/`Cart. Actual`) and exobiology (`Exo. Base`/`Exo. Full`). A running totals line at the top shows sold vs. still-pending credits for both categories. Window size/position is remembered across sessions.

Actual sold values always come straight from the ED journal — ground truth, never a formula. Estimates exist purely to flag what's worth your time before you sell.

## Settings

The following settings are configurable from the EDMC preferences panel:

- **Thresholds** — minimum cartography (scan/mapping) value, minimum exobiology species value, panel lines before scrolling
- **Overlays** — radar on/off, system summary on/off, radar size, overlay summary text colour (greyed out entirely if no overlay backend is installed)
- **Debug** — developer/debug logging

## Persistence

All data and progress is stored locally in a per-install SQLite database (`explorer.sqlite`, in EDMC's app-data folder), segmented per commander. The only network call ExplorerLite makes is its own update check against this repo's GitHub releases.

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
