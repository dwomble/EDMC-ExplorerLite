"""
SQLite schema for EDMC-ExplorerLite's self-contained store.

Deliberately minimal/denormalized -- no genus/species catalog tables; that static reference
data lives in explorer/valuation/exobiology_data.py, not the DB. See REQUIREMENTS.md and the
implementation plan for the rationale behind each table.
"""
import sqlite3

SCHEMA_VERSION = 1

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
    distance_ls REAL,
    was_discovered INTEGER,
    was_mapped INTEGER,
    mapped_efficiently INTEGER,
    estimated_scan_value INTEGER,
    estimated_mapping_value INTEGER,
    flagged_value INTEGER NOT NULL DEFAULT 0,
    has_biological_signals INTEGER NOT NULL DEFAULT 0,
    biological_signal_count INTEGER,
    estimated_exobio_value_min INTEGER,
    estimated_exobio_value_max INTEGER,
    flagged_exobio INTEGER NOT NULL DEFAULT 0,
    scanned_at TEXT,
    mapped_at TEXT,
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
    UNIQUE(body_id, genus)
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
"""

def ensure_schema(conn:sqlite3.Connection) -> None:
    """ Create tables if they don't exist yet, and stamp/verify the schema version. """
    conn.executescript(DDL)

    row = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_meta (key, value) VALUES ('version', ?)", (str(SCHEMA_VERSION),))
        conn.commit()
        return

    stored_version = int(row[0])
    if stored_version != SCHEMA_VERSION:
        # No migrations exist yet -- once the schema evolves, handle version bumps here.
        raise RuntimeError(f"explorer.sqlite schema version {stored_version} does not match expected {SCHEMA_VERSION}")
