# EDMC-ExplorerLite — Design Notes

Longer design/architecture rationale that doesn't belong inline in the code: the "why" behind
non-obvious decisions, tradeoffs considered and rejected, and real-world regressions that shaped
the current design. Each section below matches a module; that module's own docstring is now a
short pointer back here.

## explorer/ui/overlay_frames.py — Overlay radar

Draws distance rings, a ring at the current species' minimum sample distance, and a marker per
logged position, on the modern overlay backend (EDMCModernOverlay via utils/overlay.py).

**Real vs. tagged markers.** A real `ScanOrganic` sample draws a filled/hollow square in
`SAMPLE_COLOR` (blue). A `CodexEntry` waypoint tag — a passive "spotted it" note, not "currently
working on it" — draws a hollow triangle in the game's own reported variant color instead (see
`CODEX_TAG_COLORS`). Shape, not just color, is what keeps a tag from ever being mistaken for a
real sample, which also means a tag's true color is always safe to use even when it's a
blue/cyan one (color alone couldn't guarantee that). `CODEX_TAG_COLORS`' names are the full known
set of Odyssey exobiology variant colors, cross-checked against EDMC-BioScan's own color-name
list (not its hex values or code — the hex values here are our own).

**Visibility.** Shown from `SupercruiseExit` onward (flying over the surface, not just on-foot),
whenever a confirmed genus has at least one sample taken this visit. A genus that's merely been
tagged via `SAASignalsFound` but not yet approached draws nothing by default (`SHOW_TAGGED_GENUS`
is off) — there's no known bearing to it yet, only a distance, and an earlier attempt to show a
differently-colored ring + label for it either conveyed no real information or (once heading-up
was added) misleadingly suggested a direction, since the label's fixed screen anchor always
coincided with "straight ahead". Kept in the code (not deleted) in case a future presentation of
"tagged genus" info is wanted again.

Only ONE ring is ever drawn at a time — `state.current_genus`, the genus of the most recent real
`ScanOrganic` sample — since several genera's rings on screen simultaneously became illegible.
Markers for every in-progress genus still show regardless.

**Regression:** falling back to a pre-DSS genus prediction whenever there were no *active*
genera (rather than no genera confirmed AT ALL) meant a body with every genus already fully
sampled could resurrect a stale prediction and keep the radar showing, instead of hiding once
there's genuinely nothing left to scan. Fixed by checking `all_progress` too, mirroring
`panel.py`'s own equivalent guard.

**Heading-up rotation.** The player's current facing direction always maps to screen "up", so the
whole radar (rings excepted — concentric circles look the same either way — but sample markers)
rotates as you turn, rather than a separate tick line showing facing against a fixed north-up
frame. Sample markers are positioned relative to the player's CURRENT position and heading each
call, so they correctly drift/rotate as the player walks/turns, same as a real heading-up radar.

**Distance scale.** Started as fixed rings on a linear scale, then a true logarithmic scale (each
distance-doubling "octave" getting equal pixel width), before settling on the current
piecewise-linear design. The log scale had a real problem: anchoring it so the 200m ring sat at a
clean 25% left no room below 200m, so any genus with a *smaller* minimum distance (several are
exactly 100m) would collapse to a degenerate, zero-radius ring at dead center. A true log scale
also can't reach exactly 0m (only approach it asymptotically), so it always needs an arbitrary
floor constant.

The final design (`_radius_frac()`) is piecewise-linear instead: 3 rings (`RING_DISTANCES_M` —
200/600/1400m) evenly spaced in pixels (thirds), each segment covering DOUBLE the real-world
width of the one before it (200m, then 400m, then 800m). This keeps the "closer = finer
resolution, farther = coarser" property of a log scale, but starts at a genuine 0m at dead
center with no arbitrary floor — every known genus's minimum sample distance (100m up to
Electricae's 1000m) lands at a clearly visible, non-degenerate radius well inside the outermost
ring.

The outermost ring (1400m) doesn't sit at the very edge of the radar. The radar's TRUE edge is
`EDGE_DISPLAY_M` (1500m), reserving a thin margin band (`RING_AREA_FRAC` of the radius is the
labeled/ring-covered zone; the rest is the margin) for out-of-range dots, which sit at the
midpoint of that band — clear of the ring line, and never exceeding the user-configured radar
size (the earlier approach pushed them a fixed pixel amount past the full radius, which could
exceed it).

Because the scale is non-linear, a sample's screen position can't be computed by rotating and
then scaling its real (east, north) offset directly (that only works for a *linear* scale) — the
bearing (a unit direction, rotated to heading-up) and the pixel radius (from `_radius_frac`) have
to be computed separately and combined afterward.

**`_ensure_group()` kwarg naming:** confirmed against EDMCModernOverlay's actual `overlay_api.py`
source, a newer release renamed `define_plugin_group`'s kwargs (`plugin_group` -> `plugin_name`,
`matching_prefixes` -> `plugin_matching_prefixes`, `id_prefix_group` -> `plugin_group_name`,
`id_prefixes` -> `plugin_group_prefixes` — the old snake_case names are still accepted as
deprecated aliases, just logged as a warning) and requires `plugin_group_prefixes` whenever a new
`plugin_group_name` is being created. An earlier fix here guessed the wrong replacement name
(camelCase `idPrefixes`, which isn't a recognized argument under either name) — confirmed correct
against the real source.

No explicit "clear" — every shape is sent with a short TTL and simply stops being refreshed (and
expires on the overlay) once `render()` stops being called for this genus/body, which happens
naturally once the panel/dispatch flags say the overlay is no longer relevant.

## explorer/ui/panel.py — Exobiology section & predicted rows

**No header on the on-body exobiology detail.** It's silent for a body with no biological
interest at all, unless the player is actually on-foot there (showing "nothing here" for every
uninteresting body/star/gas giant flown past would drown out the rest of the panel; on-foot,
it's confirmation the player actually wants). It nests directly under the current body's own
flagged row in `_render_system_summary`, which already names the body — an earlier version added
a separate header line here too, which just duplicated the row directly above it. Fixed by
removing the header and interleaving the detail under the row instead of after the whole table.

**`_best_predictions_for_body`'s tie handling.** Within a genus, several species often tie at
the same top confidence — one is picked (chain-tier preference, see `signal_count_bias.py`) as
the display name, but the value range spans every tied alternate, not just the one shown, so a
silent single pick doesn't understate what's genuinely still possible (e.g. a lower-value
species winning the tiebreak while a much higher-value one ties right alongside it). Each chain
tier counts as ONE slot, not several — a tier can be ambiguous between its own alternatives (e.g.
Osseus-or-Tubus) but that's still a single real signal slot, and a slot containing a chain unit
is prioritized over a same-or-lower-confidence non-chain slot (the signal-count pattern is
stronger evidence than a marginal condition-matching gap). Within a single confidence-tied
group, chain membership only decides which subset gets an individual slot when the group is too
big to fit all its members — it never lets the chain pick one tied candidate over another as if
it were certain. A too-big group keeps as many individual slots as it can (chain-tier order
first) and folds only the true excess into one final merged slot.

**`_exobio_row_range`'s narrowing.** Once a genus is confirmed but not yet sampled, its value
range narrows to the surviving Scan-time species predictions for that genus+body, not the
genus's full unnarrowed range — confirming the genus doesn't mean every species of it is still
equally plausible, only the ones whose spawn conditions actually matched this body. Falls back
to the full genus range only when there's no species-level prediction data at all (e.g. a genus
outside `species_conditions.py`'s coverage). Regression: an earlier version used the full range
here even when a narrower prediction already existed, so the displayed estimate would widen
right after confirmation — it should only ever narrow as more is learned.

## explorer/valuation/genus_conditions.py — Spawn-condition data

**Why rulesets are OR'd, not a single blob per genus.** An earlier attempt modeled one
condition-blob per genus, which silently dropped real spawn niches — e.g. Bacterium is
genuinely absent from Sulphur Dioxide atmospheres in one species' data but present via two
others, and a single genus-wide blob can't represent that. A real body is eligible for a genus
if it satisfies ANY ONE of that genus's rulesets, mirroring the game's actual
per-species-per-atmosphere condition structure. Per-species distinctions are still deliberately
flattened to genus level (all of a genus's species' rulesets pooled together) — this plugin
predicts genus only, matching its existing scope decision not to guess species.

**"unmodeled" tags.** Several rulesets carry a `# unmodeled: ...` comment noting real spawn
conditions that don't fit the fields available from a `Scan` event: system-wide co-occurrence
checks ("bodies"), galactic region/nebula/Guardian-ruin proximity ("regions"/"nebula"/
"guardian"/"tuber"), a specific home system ("system"), atmosphere gas percentage floors
("atmosphere_component"), orbital period, or distance-from-arrival bounds. Those specific
conditions are simply not checked — the ruleset still applies based on whatever fields it does
have, so predictions for genera whose only rulesets carry these (Bark Mound, Amphora Plant,
Crystalline Shard, some Anemone/Brain Tree/Sinuous Tuber rulesets) will over-fire outside their
real niche. Accepted, not solved — flagged per-ruleset so the gap is visible.

**Sourcing.** Read Silarn/EDMC-BioScan (github.com/Silarn/EDMC-BioScan, GPLv2) locally as a
reference and independently transcribed/restructured the numeric spawn parameters into this
project's own dataclass shape and code — not copying its files, data structures, or prose. This
project stays permissively (MIT) licensed; BioScan is read-only reference material for
verifying facts, same policy as `exobiology_data.py`'s own sourcing.

## explorer/valuation/cartography.py — Cartography value estimate

Deliberately approximate: community-documented formula constants for Elite Dangerous's
exploration payouts are contested across sources and may have shifted across game-balance
patches. This module's only job is producing a number good enough to compare against the
user's "worth flagging" credit threshold — it's never used for the "actual" accumulated
totals, which come straight from `SellExplorationData`/`MultiSellExplorationData` journal
events (ground truth, no formula involved). Constants are kept isolated here so they're easy
to recalibrate later. Base-k and terraform-k constants are cross-checked against two
independent community sources (Frontier forums' "Exploration value formulae" thread +
corroborating discussion elsewhere).

**Regression:** "High metal content body" previously fell through to the generic "default" k
(720) since it was never a matched category — a Terraformable HMC's real payout is dominated
almost entirely by the terraform bonus, so that gap silently under-valued exactly the bodies
most worth flagging. Fixed by giving it (and "Rocky body") their own base/terraform-k pair.

## explorer/valuation/genus_prediction.py — Pre-DSS genus/species prediction

Reads the raw `Scan` (Detailed) entry dict directly (same convention as `cartography.py`), not
a typed wrapper. A genus/species is eligible if the body satisfies ANY ONE of its rulesets from
`genus_conditions.py`/`species_conditions.py` (rulesets OR'd, fields within one ruleset AND'd).
Categorical fields (atmosphere, body type, star type, volcanism) are hard gates. Temperature/
gravity/pressure are soft: confidence tapers from 1.0 inside a ruleset's documented range down
to 0.0 over a margin beyond either edge, since a transcribed range can't be trusted to the exact
Kelvin/G — a near-miss should read as lower confidence, not an identical hard fail. A
genus/species's overall confidence is the best (max) score across its matching rulesets, since
each is an independent, alternative path to eligibility, not a combined requirement.

## explorer/valuation/exobiology_data.py — Species value data

**Sourcing.** Clean-room, sourced from the Elite Dangerous Fandom wiki's "Exobiology Sample
Values and Details" page, cross-checked against njthomson/SrvSurvey's "Organic Scanning"
reference (independent source, matched exactly on every genus/distance) — see REQUIREMENTS.md
for the licensing rationale (keeps this plugin permissively licensed, no GPL entanglement with
BioScan's data).

**Excluded scope.** Thargoid biologicals (Spires, Mega Barnacles, Coral Tree, Coral Root) are
tied to Thargoid structure sites rather than ordinary planetary exploration, and it's
unconfirmed whether they even use the same ScanOrganic/Genetic-Sampler mechanic — out of scope
for a general exploration assistant, revisit if that changes.

**Genus_Localised plurality caveat.** The exact in-game string for three genera (singular vs.
plural) is unconfirmed: "Sinuous Tuber(s)", "Bark Mound(s)", "Crystalline Shard(s)". The Fandom
wiki titles them singular; a tool that parses live journals (SrvSurvey) uses plural. Singular is
used as the dict key; verify against a real captured journal line and correct if needed.

## explorer/db/schema.py — genus_predictions species-column migration

v3->v4 gave `genus_predictions` a `species` column and relaxed its UNIQUE constraint to
`(body_id, genus, species)`, so several candidate species within one genus can coexist
(species-level narrowing, see `valuation/species_conditions.py`). SQLite can't ALTER a UNIQUE
constraint in place. But this table is fully derived/ephemeral —
`replace_genus_predictions()` deletes and reinserts it in full on every `Scan` event — so
dropping it and letting the DDL recreate it fresh is simpler and safer than hand-rolling a real
data migration for rows that regenerate themselves within one `Scan` event anyway.

## explorer/valuation/species_conditions.py — Per-species narrowing data

Scoped to atmosphere-bearing genera only — landable bodies are always <=0.1 atm, so there's no
missing "thick atmosphere" case to source. Airless genera (Amphora Plant, Anemone, Bark Mound,
Brain Tree, Sinuous Tuber, Crystalline Shard) are absent here and stay genus-only via
`GENUS_RULESETS` (see `genus_prediction.predict_species()`). Sourced the same way as
`genus_conditions.py`: Silarn/EDMC-BioScan (GPLv2) read locally as a fact source, transcribed
independently, not copied — cross-checked against ed-dsn.net's community temperature-band page,
which agreed closely.

## explorer/valuation/signal_count_bias.py — Signal-count chain heuristic

`biological_signal_count` (FSSBodySignals' exact count of distinct genus signals) provides a
soft ranking bias, layered on top of — never replacing — `genus_prediction.py`'s real
confidence scoring: a tiebreak among already-eligible candidates only, never granting
eligibility on its own. Cumulative by tier (1..`MAX_CHAIN_SIGNAL_COUNT`): tiers 1..N stay
expected even when the body's real signal count runs higher than `MAX_CHAIN_SIGNAL_COUNT` —
extra signals beyond that are just unclassified, not evidence the earlier tiers stopped
applying. No bias at all on Thin Water/Oxygen/Nitrogen bodies.

**Regression:** a tier-1 "hot HMC -> Stratum Tectonicas" override used to live here; removed
after real journal data showed it wrongly beating a confirmed Bacterium (Stratum Tectonicas's
own range is wide enough to be "eligible" on almost any warm HMC body).

## explorer/journal/handlers_exobiology.py — CodexEntry waypoint tagging

The low-altitude composition scanner (ship or SRV) fires `CodexEntry` whenever it identifies a
biological signal — for genuinely new discoveries and re-scans of already-known ones alike —
carrying an exact Latitude/Longitude, unlike `SAASignalsFound`'s aggregate genus+count. Useful
for tagging a waypoint to a species spotted but not currently being sampled (e.g. scanning
something else nearby). Reuses `state.sample_positions`, the same session-only, radar-only
store `ScanOrganic` feeds, so it gets a ring + dot immediately without touching
`samples_taken`/`species_progress` completion — never mistaken for a real genetic sample in the
panel's progress counts. `Name_Localised` also gives the exact species (not just genus), so it
confirms the species/value the same way a real sample eventually would, replacing whatever
"possible species" guess was showing well before landing and sampling it. Its color variant
(e.g. "Tussock Cultro - Yellow") is stashed alongside the position too, so the radar can draw it
in that color instead of the plain sample-taken blue — these are passive tags, not "currently
working on it", and looked identical to real samples otherwise. A tag within the genus's minimum
sample distance of a real sample already taken is never even added as a waypoint — it couldn't
produce a valid additional sample, so it'd just be sending the player somewhere pointless.

## explorer/journal/handlers_context.py — Session restore & cold start

EDMC doesn't replay journal history to plugins on restart, so without `restore_last_session()`
the panel sits at "Explorer -- idle" until the next live event -- annoying if the player isn't
even logged into the game yet. It presumes nothing changed since the last session (same Cmdr,
same system/body); `enter_system()`'s own cold-start check layers on top once a real
Location/FSDJump arrives, correcting anything actually different (a different Cmdr, a system
change while EDMC was closed).

**Regression:** `state.restored_at_startup` exists because `enter_system()`'s cold-start check
used to be just `state.system_id is None` -- but `restore_last_session()` pre-populates
`system_id` before any real event arrives, so that check silently passed and treated a restored
session as *not* a cold start, breaking the resume logic entirely. Fixed by tracking
`restored_at_startup` explicitly and treating it as an equally valid cold-start signal,
cleared once consumed. `on_load_game()` also had to skip its own persist call while this flag is
still set, so it doesn't overwrite the resumable snapshot on disk before `enter_system()` reads it back.

## explorer/db/store.py — DB location

`resolve_db_path()` stores the DB under `config.app_dir_path` (EDMC's persistent app-data
directory), namespaced into the plugin's own subfolder — deliberately not inside the plugin's
own code folder (`plugin_dir`). `Updater.install()` extracts a release zip in-place via
`zipfile.extractall(plugin_dir)`, which doesn't wipe existing files, so a `plugin_dir/data/`
subfolder would survive that update path — but a manual reinstall (delete-and-reclone, or
EDMC's own plugin uninstall/reinstall) wipes `plugin_dir` outright, which would destroy a
Cmdr's entire scan history. `config.app_dir_path` is shared across EDMC and other plugins, but
namespacing this plugin's own subfolder under it avoids collision while surviving any
plugin-folder replacement.
