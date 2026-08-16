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

**Regression:** `_planet_category()`'s substring checks are naive (`"ammonia" in planet_class`),
so "Gas giant with ammonia based life" collided with the unrelated "Ammonia world" category and
got its much higher k (232,619) — showing 3.39M Cr for a body a real first-discovery+DSS-mapped
payout put at ~11,000 Cr. No dedicated gas/water-giant k is sourced; confirmed against that real
payout that "default" is the right bucket at typical gas-giant mass. Fixed by checking
"gas giant"/"water giant" first, before the categories they'd otherwise collide with.

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

## First-discovery/first-mapped/first-logged bonus tracking

**Sourcing.** Elite Dangerous pays a bonus on top of the base value for cartography and
exobiology when nobody else has claimed the relevant discovery yet. Confirmed against a real
captured journal log (a `Scan` event on the same body carries `WasDiscovered`, `WasMapped`,
AND `WasFootfalled` booleans side by side) and against the user's own stated mechanics:
- First Discovered By: +60% to the base scan (honk/FSS) value.
- First Mapped By: +60% to the DSS mapping value.
- First Footfall (exobiology's proxy): a body nobody has ever walked on yet means nobody could
  have sampled its organics either, so the exobio first-logged bonus (5x total, i.e. base + 4x
  bonus -- already a documented constant, `exobiology_data.FIRST_LOGGED_BONUS_MULTIPLIER`)
  applies. `WasFootfalled` is a proxy, not proof -- someone could have footfallen the body
  without sampling the specific species found, but it's the best signal the game exposes (the
  same proxy the reference plugin EDMC-BioScan uses, confirmed by reading its source locally:
  it hardcodes the identical `5` multiplier gated on the same signal).

**Storage: base only.** `bodies.was_discovered`/`was_mapped`/`was_footfalled` are captured
verbatim from the `Scan` event (`handlers_bodies.on_scan`). The stored `estimated_scan_value`/
`estimated_mapping_value` columns, and `species_progress.confirmed_value`, stay BASE (bonus
never baked in) -- every consumer (panel, history, threshold checks) applies the bonus fresh
from the flags at its own point of use, via `cartography.scan_value_with_bonus()`/
`mapping_value_for_eligibility()` and `exobiology.with_first_logged_bonus()`. This avoids ever
double-counting a bonus that got baked into a stored number and then re-applied downstream.

**Cartography asymmetry, deliberate.** `estimate_scan_value()` stays base-only (unchanged,
its existing meaning); `scan_value_with_bonus()` ADDS the +60% when `not was_discovered`.
`estimate_mapping_value()` -- and the `FIRST_MAPPED_MULTIPLIER` (3.7) constant it's built on --
already assumed first-mapped-by-us (its existing, unchanged docstring/meaning, predating this
feature). Rather than decompose that already-approximate constant to make it symmetrical with
scan value (risking compounding guesswork about exactly how 3.7 was originally derived),
`mapping_value_for_eligibility()` instead BACKS OUT the assumed +60% when `was_mapped` says
someone else already has -- the common case (nobody's mapped it) needs no adjustment at all,
preserving 3.7's original calibration and every existing test that depended on it.

**Exobiology: Base vs Full.** ED's own progression only counts the base value, never the
first-logged bonus -- so `confirmed_value` (species_progress) and history's "Exo. Base" column
stay bonus-free always. "Exo. Full" (and the compact panel's single exobio number, which always
shows Full -- the real payout matters more than progression when deciding whether to bother)
is `sold_value` once actually sold, else `with_first_logged_bonus(confirmed_value,
was_footfalled)` projected. `mark_all_completed_species_sold()` was split into
`get_completed_unsold_species_for_cmdr()` + `mark_species_progress_sold()` so
`handlers_exobiology.on_sell_organic_data` can compute each row's presumed sold value
(including the bonus) in the handler layer rather than embedding valuation logic in the store.

**Threshold checks use Full, not Base.** `on_scan()`'s `flagged_value` decision and
`_worthwhile_predictions()`/`on_saa_signals_found()`'s `flagged_exobio` decision all compare
against the bonus-inclusive value -- a body only worth flagging WITH the bonus is still worth
flagging, and `WasDiscovered`/`WasMapped`/`WasFootfalled` are already known by the time each of
these checks runs (same `Scan` event, or the body's already-stored flags for the later
`SAASignalsFound` check).

## explorer/valuation/honk_heuristic.py — Star-type-tiered verdict

Superseded the original crude body/non-body-count-only heuristic (and its later exotic-star
override patch) with a single star-type-tiered heuristic, since the crude version had no idea
a 3-body neutron star system is basically always worth a full FSS pass regardless of body
count. `on_honk()` reads the arrival star's `star_type` back out of the `bodies` table --
confirmed against a real captured journal log that its `Scan` (`AutoScan`) fires automatically
on jump-in, several seconds before the player manually triggers the honk (`FSSDiscoveryScan`).

Three tiers, by star type, each with its own bar for "worth a full scan": F/G/K/neutron/black
hole need only more than one known body (our only honk-time proxy for "has any planets" --
`BodyCount` doesn't break down stars vs. planets); M/L/T/Y dwarfs need 6+ bodies; everything
else (A/B/O, white dwarfs, Wolf-Rayet, etc.) needs 3+. A multi-star system uses whichever known
star gives the most generous (easiest to satisfy) tier. No star known yet by honk time (rare
timing edge case) defaults to the 3+ "other" tier. The old `NonBodyCount`-based OR condition
was dropped entirely, not folded into the new tiers -- deliberately, not an oversight.

## explorer/utils/th/scrollableframe.py — Interior never went dark

**Regression:** the panel's scrollable area stayed light-colored in dark mode, both on live
theme switch and after a restart. Root cause (confirmed by reading EDMC's real `theme.py`):
EDMC registers every plugin widget for theming via one walk over `plugin_app()`'s returned
frame, right after all plugins load -- but that walk only recurses into `tk.Frame`/`ttk.Frame`
children, not `tk.Canvas` ones, so `.interior` (which lives inside `ScrollableFrame`'s canvas)
was never reached. `.interior`'s own constructor also calls `theme.update(self)`, but that's a
no-op too -- it runs during `plugin_app()`, before EDMC's theme system has applied any theme yet
at all, so there's nothing yet for it to register against. `self._canvas` already worked around
this with its own explicit `theme.register()` call; `.interior` needed the same fix. Content
rows added later (during actual play, well after EDMC's first theme apply) self-register fine
through their own constructors -- this only affects the canvas boundary itself. Fixed upstream
in EDMC-PluginLib (this file is vendored) as well as here.

## explorer/db/store.py — get_flagged_bodies_for_system's biology guard

**Regression:** a Terraformable HMC and a Water World were both scanned as clearly worth
mapping (`flagged_value=1`, several million credits of mapping value) in the same real system,
but only the Water World showed up in the flagged list -- the HMC vanished entirely once
`FSSBodySignals` confirmed it had a geological (not biological) signal, setting
`has_biological_signals=0`. The query's `has_biological_signals IS NOT 0` guard was written as
a blanket `AND` over the whole row, when its actual purpose only applies to ONE of the four OR
branches: suppressing a stale pre-Scan `genus_predictions` guess once ground truth says there's
no biology here at all. Applied as a blanket filter, it also silently excluded bodies that
qualified for entirely unrelated reasons (`flagged_value`, `flagged_exobio`, confirmed real
biology) the moment biology was confirmed absent. Fixed by scoping the guard to just the
prediction branch: `flagged_value = 1 OR flagged_exobio = 1 OR has_biological_signals = 1 OR
(has_biological_signals IS NOT 0 AND EXISTS (...))`.

## explorer/ui/overlay_summary.py — Overlay system summary

Mirrors the compact panel's system-summary header line (`panel.system_header_line()`, extracted
to module level so both surfaces share it) plus a capped list of flagged-body lines, so "what's
left to do in this system" is glanceable without alt-tabbing to the panel. Each body line is
`_flagged_body_row()`'s own (designator, distance, gravity, value, description) tuple collapsed
to just designator/value/description -- distance and gravity are already columns on the panel's
own table, not worth the overlay's limited width.

**Reuses `ExplorerPanel._flagged_body_row()` directly** rather than re-deriving the same
value/formatting logic in a second place -- `_flagged_body_row()` is deeply threaded through
several other panel methods (predictions, exobio ranges, chain-tier merging), so duplicating it
would risk the two surfaces drifting out of sync. This is why `SystemSummaryOverlay` is
constructed in `load.py`'s `plugin_app()` (once `ExplorerPanel` exists), not alongside
`RadarOverlay` in `plugin_start3()` -- and why it shares the SAME underlying `Overlay()` backend
instance as the radar (`load.py`'s `overlay_backend` global) rather than probing a second time.

**No cap on how many bodies get row-computed, only on how many get shown** -- `render()`
computes `_flagged_body_row()` for every body `get_flagged_bodies_for_system()` returns, then
truncates to `MAX_BODY_LINES`. This mirrors `panel.py`'s own refresh(), which already
recomputes every row fresh on each call; a system with a genuinely huge flagged list is rare
enough that this wasn't worth optimizing pre-truncation.

**Triggered on the same "overlay" flag as the radar** (`load.py`'s `_apply_flags()`), not a
separate "panel" trigger -- `dashboard_entry` emits `{"overlay": "radar"}` every ~1/sec tick
regardless of whether anything changed, which is what keeps the radar's short-TTL frames
continuously refreshed. Piggybacking on that same flag gives the summary the same steady
cadence; gating it on "panel" instead (which only fires on discrete journal events) would let
its TTL expire and the whole overlay vanish during any stretch of supercruise with no new
events. Cartography/exobio handlers that only return `{"panel": True}` (Scan, FSSBodySignals,
SAASignalsFound) still reach the overlay within about a second via the next dashboard tick --
imperceptible in practice, not worth wiring a second explicit trigger for.

**Gating differs from the radar's.** Shown whenever `state.system_id` is known, not restricted
to on-foot/landed/lat-long -- unlike the radar (which needs a body and surface position to mean
anything), "what's left in this system" is relevant from the moment you arrive until you leave,
including while docked. No dedicated "docked" suppression exists yet (`ExplorerState` doesn't
track it) -- accepted for now rather than adding new journal-event tracking speculatively.

**Refinements after real-world use:**
- **TTL bumped 8s -> 30s.** Real-world reports of the summary going blank between refreshes
  despite sharing the radar's own steady dashboard-tick trigger -- rather than fully diagnose
  the cadence, a much longer TTL is a safe hedge against however irregular it turns out to be.
- **System name dropped from the header** (`system_status_text()`, no name, vs.
  `system_header_line()` which prepends it for the panel) -- the game's own UI already shows
  the current system name elsewhere, so repeating it here was wasted space.
- **"scan needed" replaced with live "N of M scanned" progress**
  (`store.count_scanned_bodies_for_system()` vs. `honk_body_count`), while the honk heuristic
  says the system is worth a full FSS pass. The "probably quiet"/"done" case is left alone --
  that's the heuristic's own opinion, not literal scan completion, so a scanned-count doesn't
  apply to it the same way.
- **Text colour is now a preference** (`CFG_OVERLAY_SUMMARY_TEXT_COLOR`, a `tkinter.colorchooser`
  picker in prefs.py, following the same pattern as another of the user's plugins,
  EDMC-NeutronDancer) -- read fresh each render, matching how radar size is already configurable.
- **Biologically-interesting bodies now sort first**, before the `MAX_BODY_LINES` cap is
  applied. Real regression: the list was plain `body_id` order, so a body with confirmed
  biology could silently land in the anonymous "+N more" overflow behind several
  cartography-only bodies with lower body IDs -- exactly backwards for a plugin whose main
  point is exobiology. `_sort_key()` treats `has_biological_signals`/`flagged_exobio`/
  `has_prediction` as "biological interest" and sorts those bodies before pure-cartography
  ones; a stable sort keeps body_id order within each group.

**Current-body species detail (`_current_body_lines()`).** The overlay originally mirrored
only the top-level flagged-body list -- real feedback after using it live was that the
per-species detail table the panel shows for whichever body you're actually standing on
(`ExplorerPanel._render_exobiology_section()`, e.g. "Bacterium Aurasus 2/3 500m 5M Cr") was
missing entirely, a genuine scope gap rather than a bug in what was already built. Added as a
new section below the flagged-body list, reusing `_exobio_progress_row()`/
`_predicted_genus_row()`/`_best_predictions_for_body()` directly and mirroring
`_render_exobiology_section()`'s exact selection logic (active samples this visit, else a
pre-DSS prediction, else nothing) so the two surfaces can't drift apart. No header/body-name
line -- same as the panel's own nesting, which already sits directly under the body's own
row with nothing labeling it; the overlay ties the lines back to their body the same way,
via `CURRENT_BODY_INDENT_PX` (an indented x-offset, not leading whitespace in the text) rather
than repeating the body's name. Row position on screen is dynamic -- it starts right after
however many flagged-body/overflow lines were actually shown that tick, the same way the
overflow line itself already floats.

**Stale slots now clear immediately instead of waiting out their TTL.** Real regression: a
mapped body's row disappeared from the panel right away (`on_saa_scan_complete()` only returns
`{"panel": True}`, refreshing the panel synchronously) but lingered on the overlay for up to a
full TTL, since the overlay only re-evaluates on the next dashboard tick and previously relied
entirely on a dropped frame's own TTL expiry to disappear -- fine at the original TTL (8s), but
once TTL was bumped to 30s (see above) a stale, no-longer-true line could visibly linger for
that long. `render()` now tracks how many body/current-body lines (and whether an overflow
line) it drew last time, and explicitly `overlay.clear()`s exactly the slots no longer in use
-- same fix applied to every early-return branch (disabled in settings, no system known, etc.)
so those also clear immediately rather than fading out over TTL. This keeps the longer TTL
fixing "not staying up long enough" without reintroducing "stays up too long after it
shouldn't" -- the two complaints are only in tension if disappearance depends on TTL at all.

## explorer/journal/handlers_bodies.py — Belt clusters aren't scannable bodies

**Regression:** "N of M scanned" (see the summary overlay above) could read something like "20
of 9 scanned" -- more scanned than the honk itself ever reported existing. Root cause: an
asteroid belt cluster's own `Scan` (`AutoScan`) event has neither `StarType` nor `PlanetClass`
at all (confirmed against a real captured journal log), but `on_scan()` didn't check for that,
so it created a fake "Planet" body row for every belt cluster and stamped it `scanned_at` just
like a real body -- inflating `count_scanned_bodies_for_system()` well past
`honk_body_count` (which only counts real bodies; a belt cluster is exactly what
`NonBodyCount` is for). It was also getting a bogus cartography value estimate from
`cartography.estimate_scan_value()`'s `PlanetClass`-less default-category fallback, though
that never surfaced as visibly as the scanned-count inflation did. Fixed by returning early
whenever neither field is present -- a belt cluster is never tracked as a body at all now, not
patched after the fact.
