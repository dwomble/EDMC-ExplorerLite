"""
SQLite schema for EDMC-ExplorerLite's self-contained store.

Deliberately minimal/denormalized -- no genus/species catalog tables; that static reference
data lives in explorer/valuation/exobiology_data.py, not the DB. See REQUIREMENTS.md and the
implementation plan for the rationale behind each table.
"""
import sqlite3
from contextlib import closing

from explorer.utils.debug import Debug

SCHEMA_VERSION = 12

DDL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS cmdrs (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    fid TEXT,
    actual_cartography_credits INTEGER NOT NULL DEFAULT 0,
    actual_exobiology_credits INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS systems (
    id INTEGER PRIMARY KEY,
    cmdr_id INTEGER NOT NULL REFERENCES cmdrs(id),
    system_address INTEGER NOT NULL,
    name TEXT NOT NULL,
    honk_body_count INTEGER,
    honk_non_body_count INTEGER,
    honk_hint TEXT,
    all_bodies_found INTEGER NOT NULL DEFAULT 0,
    fss_body_count INTEGER,
    visited_at TEXT,
    sold_at TEXT,
    lost_at TEXT, -- held cartography data lost (ship destroyed) rather than sold
    UNIQUE(cmdr_id, system_address)
);

CREATE TABLE IF NOT EXISTS bodies (
    id INTEGER PRIMARY KEY,
    cmdr_id INTEGER NOT NULL REFERENCES cmdrs(id),
    system_id INTEGER NOT NULL REFERENCES systems(id),
    body_id INTEGER NOT NULL,
    body_name TEXT NOT NULL,
    body_type TEXT,
    star_type TEXT,
    planet_class TEXT,
    atmosphere_type TEXT, -- raw AtmosphereType string, e.g. "CarbonDioxide", "None" -- used by
    -- valuation/signal_count_bias.py to detect its Water/Oxygen/Nitrogen exception
    distance_ls REAL,
    surface_gravity REAL, -- raw SurfaceGravity, m/s^2 (convert to G for display)
    was_discovered INTEGER,
    was_mapped INTEGER,
    was_footfalled INTEGER, -- ground truth from Scan's WasFootfalled -- proxy for exobio first-logged bonus eligibility
    mapped_efficiently INTEGER,
    estimated_scan_value INTEGER,
    estimated_mapping_value INTEGER,
    flagged_value INTEGER NOT NULL DEFAULT 0,
    has_biological_signals INTEGER, -- NULL = not yet checked (FSSBodySignals hasn't fired); 0/1 = confirmed absent/present
    biological_signal_count INTEGER,
    estimated_exobio_value_min INTEGER,
    estimated_exobio_value_max INTEGER,
    flagged_exobio INTEGER NOT NULL DEFAULT 0,
    scanned_at TEXT,
    mapped_at TEXT,
    type_label TEXT, -- short display abbreviation, e.g. "T HMC", "ELW"
    UNIQUE(cmdr_id, system_id, body_id)
);

CREATE TABLE IF NOT EXISTS body_genuses (
    id INTEGER PRIMARY KEY,
    body_id INTEGER NOT NULL REFERENCES bodies(id),
    genus TEXT NOT NULL,
    signal_count INTEGER,
    revealed_by TEXT NOT NULL,
    UNIQUE(body_id, genus)
);

CREATE TABLE IF NOT EXISTS species_progress (
    id INTEGER PRIMARY KEY,
    body_id INTEGER NOT NULL REFERENCES bodies(id),
    genus TEXT NOT NULL,
    species TEXT,
    variant TEXT,
    samples_taken INTEGER NOT NULL DEFAULT 0,
    last_stage TEXT,
    first_sample_at TEXT,
    last_sample_at TEXT,
    completed_at TEXT,
    estimated_value_min INTEGER,
    estimated_value_max INTEGER,
    confirmed_value INTEGER,
    sold INTEGER NOT NULL DEFAULT 0,
    sold_value INTEGER,
    sold_at TEXT,
    lost_at TEXT, -- completed data lost (ship destroyed) before it could be sold
    UNIQUE(body_id, genus, species) -- one row per species, a body can host several of a genus
);

CREATE TABLE IF NOT EXISTS sale_events (
    id INTEGER PRIMARY KEY,
    cmdr_id INTEGER NOT NULL REFERENCES cmdrs(id),
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    system_name TEXT,
    total_value INTEGER NOT NULL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS genus_predictions (
    id INTEGER PRIMARY KEY,
    body_id INTEGER NOT NULL REFERENCES bodies(id),
    genus TEXT NOT NULL,
    species TEXT, -- NULL = genus-only guess (no species-level ruleset data for this genus)
    confidence REAL NOT NULL,
    UNIQUE(body_id, genus, species)
);

-- Real samples only -- radar marker restart recovery.
CREATE TABLE IF NOT EXISTS sample_positions (
    id INTEGER PRIMARY KEY,
    body_id INTEGER NOT NULL REFERENCES bodies(id),
    genus TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL
);
"""

# Columns added to a table that already existed in an earlier schema version -- unlike brand
# new tables (CREATE TABLE IF NOT EXISTS handles those for free), an existing table needs a
# real ALTER TABLE to pick up a new column. (table, column, coltype) -- keep this list
# additive only; a rename/removal still needs real migration code, not this helper.
COLUMN_ADDITIONS:list[tuple[str, str, str]] = [
    ("bodies", "type_label", "TEXT"),
    ("bodies", "atmosphere_type", "TEXT"),
    ("bodies", "surface_gravity", "REAL"),
    ("bodies", "was_footfalled", "INTEGER"),
    ("bodies", "volcanism", "TEXT"),
    ("bodies", "landable", "INTEGER"),
    ("bodies", "materials", "TEXT"), # JSON {name: percent} from Scan
    ("systems", "lost_at", "TEXT"),
    ("species_progress", "lost_at", "TEXT"),
    ("species_progress", "sold_at", "TEXT"),
]

def _ensure_columns(conn:sqlite3.Connection) -> None:
    for table, column, coltype in COLUMN_ADDITIONS:
        existing:set[str] = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
    conn.commit()

def _migrate_genus_predictions_species_column(conn:sqlite3.Connection) -> None:
    """ v3->v4: genus_predictions gains a species column -- dropped and DDL-recreated since it's fully derived. """
    tables:set[str] = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "genus_predictions" not in tables:
        return
    columns:set[str] = {row[1] for row in conn.execute("PRAGMA table_info(genus_predictions)")}
    if "species" not in columns:
        conn.execute("DROP TABLE genus_predictions")
        conn.commit()

def _migrate_progress_unique(conn:sqlite3.Connection) -> None:
    """ v10->v11: species_progress was UNIQUE(body_id, genus), set aside here and copied back after the DDL recreates it. """
    row:sqlite3.Row|None = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'species_progress'").fetchone()
    if not row or "UNIQUE(body_id, genus)" not in row[0]: return

    conn.execute("ALTER TABLE species_progress RENAME TO species_progress_old")
    conn.commit()

def _copy_progress_back(conn:sqlite3.Connection) -> None:
    tables:set[str] = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "species_progress_old" not in tables: return

    old:set[str] = {row[1] for row in conn.execute("PRAGMA table_info(species_progress_old)")}
    new:set[str] = {row[1] for row in conn.execute("PRAGMA table_info(species_progress)")}
    cols:str = ", ".join(sorted(old & new))
    conn.execute(f"INSERT INTO species_progress ({cols}) SELECT {cols} FROM species_progress_old")
    conn.execute("DROP TABLE species_progress_old")
    conn.commit()

def ensure_schema(conn:sqlite3.Connection) -> None:
    """ Create tables if they don't exist yet, add any new columns, and stamp/verify the schema version. """
    has_meta:bool = conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'schema_meta'").fetchone() is not None
    old:sqlite3.Row|None = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone() if has_meta else None
    file:str = conn.execute("PRAGMA database_list").fetchone()[2]
    if old and file and int(old[0]) < SCHEMA_VERSION:
        try:
            with closing(sqlite3.connect(f"{file}.v{old[0]}.bak")) as dest: conn.backup(dest)
        except (sqlite3.Error, OSError) as e:
            Debug.logger.warning(f"Could not back up {file} before upgrading its schema: {e}")

    _migrate_genus_predictions_species_column(conn) # must run BEFORE the DDL recreates the table
    _migrate_progress_unique(conn) # likewise
    conn.executescript(DDL)
    _copy_progress_back(conn)
    _ensure_columns(conn)

    row:sqlite3.Row|None = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_meta (key, value) VALUES ('version', ?)", (str(SCHEMA_VERSION),))
        conn.commit()
        return

    stored_version:int = int(row[0])
    if stored_version > SCHEMA_VERSION:
        raise RuntimeError(f"explorer.sqlite schema version {stored_version} is newer than this plugin supports ({SCHEMA_VERSION}); "
                           f"restore the .v{SCHEMA_VERSION}.bak backup next to it to use this version")
    if stored_version < SCHEMA_VERSION:
        # New tables are handled by the DDL script above; new columns on existing tables by
        # _ensure_columns(). This just stamps the version once both have run. A future
        # non-additive change (column rename/removal) would still need real migration code.
        conn.execute("UPDATE schema_meta SET value = ? WHERE key = 'version'", (str(SCHEMA_VERSION),))
        conn.commit()
