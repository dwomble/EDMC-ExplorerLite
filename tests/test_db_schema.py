"""
Unit test for the schema migration path (explorer/db/schema.py). No DB/journal/Tk harness
needed -- builds a raw sqlite3 connection directly.

Run with:
    .venv/bin/python -m pytest tests/test_db_schema.py -v --tb=short
"""
import sqlite3

import pytest

from explorer.db.schema import ensure_schema, SCHEMA_VERSION

# The pre-genus_predictions (v1) DDL, frozen here on purpose -- this is what ensure_schema()
# must be able to upgrade from, not what it currently creates.
V1_DDL = """
CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE cmdrs (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    fid TEXT,
    actual_cartography_credits INTEGER NOT NULL DEFAULT 0,
    actual_exobiology_credits INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE systems (
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

CREATE TABLE bodies (
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

CREATE TABLE body_genuses (
    id INTEGER PRIMARY KEY,
    body_id INTEGER NOT NULL REFERENCES bodies(id),
    genus TEXT NOT NULL,
    signal_count INTEGER,
    revealed_by TEXT NOT NULL,
    UNIQUE(body_id, genus)
);

CREATE TABLE species_progress (
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

CREATE TABLE sale_events (
    id INTEGER PRIMARY KEY,
    cmdr_id INTEGER NOT NULL REFERENCES cmdrs(id),
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    system_name TEXT,
    total_value INTEGER NOT NULL,
    raw_json TEXT
);
"""

# v2 added genus_predictions as a new table but never gave `bodies` a type_label column --
# that's the v2->v3 column-addition step ensure_schema() must handle via real ALTER TABLE.
V2_EXTRA_DDL = """
CREATE TABLE genus_predictions (
    id INTEGER PRIMARY KEY,
    body_id INTEGER NOT NULL REFERENCES bodies(id),
    genus TEXT NOT NULL,
    confidence REAL NOT NULL,
    UNIQUE(body_id, genus)
);
"""

def _v1_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(V1_DDL)
    conn.execute("INSERT INTO cmdrs (name) VALUES ('Testy')")
    conn.execute("INSERT INTO schema_meta (key, value) VALUES ('version', '1')")
    conn.commit()
    return conn

def _v2_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(V1_DDL)
    conn.executescript(V2_EXTRA_DDL)
    conn.execute("INSERT INTO cmdrs (name) VALUES ('Testy')")
    conn.execute("INSERT INTO schema_meta (key, value) VALUES ('version', '2')")
    conn.commit()
    return conn

def _v3_connection() -> sqlite3.Connection:
    """ v3: genus_predictions exists but without a `species` column, and its UNIQUE constraint
    is still (body_id, genus) -- the shape ensure_schema() must upgrade away from for
    species-level narrowing (see valuation/species_conditions.py). """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(V1_DDL)
    conn.executescript(V2_EXTRA_DDL)
    conn.execute("ALTER TABLE bodies ADD COLUMN type_label TEXT")
    conn.execute("INSERT INTO cmdrs (name) VALUES ('Testy')")
    conn.execute("INSERT INTO schema_meta (key, value) VALUES ('version', '3')")
    conn.commit()
    return conn

class TestSchemaMigration:

    def test_v1_database_upgrades_cleanly(self) -> None:
        conn = _v1_connection()

        ensure_schema(conn) # must not raise

        version:str = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()[0]
        assert int(version) == SCHEMA_VERSION

        tables:set[str] = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert "genus_predictions" in tables

        body_columns:set[str] = {row[1] for row in conn.execute("PRAGMA table_info(bodies)")}
        assert "type_label" in body_columns

    def test_v1_database_upgrade_preserves_existing_data(self) -> None:
        conn = _v1_connection()
        ensure_schema(conn)
        assert conn.execute("SELECT name FROM cmdrs WHERE name = 'Testy'").fetchone() is not None

    def test_v2_database_upgrade_adds_type_label_column(self) -> None:
        """ v2 has genus_predictions already (a new table, handled for free by CREATE TABLE IF
        NOT EXISTS) but not bodies.type_label -- a new column on an EXISTING table, which
        needs the real ALTER TABLE path in _ensure_columns(), not just the DDL script. """
        conn = _v2_connection()
        body_columns_before:set[str] = {row[1] for row in conn.execute("PRAGMA table_info(bodies)")}
        assert "type_label" not in body_columns_before # sanity check the fixture itself

        ensure_schema(conn) # must not raise

        version:str = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()[0]
        assert int(version) == SCHEMA_VERSION
        body_columns_after:set[str] = {row[1] for row in conn.execute("PRAGMA table_info(bodies)")}
        assert "type_label" in body_columns_after
        assert conn.execute("SELECT name FROM cmdrs WHERE name = 'Testy'").fetchone() is not None

    def test_v3_database_upgrade_adds_species_column_and_relaxes_uniqueness(self) -> None:
        """
        v3->v4: genus_predictions gains a `species` column and its UNIQUE constraint relaxes to
        (body_id, genus, species) -- SQLite can't ALTER a UNIQUE constraint in place, so this
        exercises the drop-and-recreate migration path (_migrate_genus_predictions_species_column).
        """
        conn = _v3_connection()
        pred_columns_before:set[str] = {row[1] for row in conn.execute("PRAGMA table_info(genus_predictions)")}
        assert "species" not in pred_columns_before # sanity check the fixture itself

        ensure_schema(conn) # must not raise

        version:str = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()[0]
        assert int(version) == SCHEMA_VERSION
        pred_columns_after:set[str] = {row[1] for row in conn.execute("PRAGMA table_info(genus_predictions)")}
        assert "species" in pred_columns_after

        # The relaxed UNIQUE(body_id, genus, species) must allow several candidate species
        # within the same genus for the same body (the whole point of species-level narrowing).
        body_id:int = conn.execute("INSERT INTO bodies (cmdr_id, system_id, body_id, body_name) VALUES (1, 1, 1, 'Test 1')").lastrowid
        conn.execute("INSERT INTO genus_predictions (body_id, genus, species, confidence) VALUES (?, 'Tussock', 'Tussock Ignis', 0.9)", (body_id,))
        conn.execute("INSERT INTO genus_predictions (body_id, genus, species, confidence) VALUES (?, 'Tussock', 'Tussock Pennata', 0.7)", (body_id,)) # must not raise
        conn.commit()
        rows = conn.execute("SELECT species FROM genus_predictions WHERE body_id = ? ORDER BY confidence DESC", (body_id,)).fetchall()
        assert [row["species"] for row in rows] == ["Tussock Ignis", "Tussock Pennata"]

        assert conn.execute("SELECT name FROM cmdrs WHERE name = 'Testy'").fetchone() is not None

    def test_ensure_schema_is_idempotent_on_an_up_to_date_database(self) -> None:
        """ ALTER TABLE ADD COLUMN on a column that already exists raises in SQLite -- calling
        ensure_schema() twice (e.g. two ExplorerStore instances against the same file) must not. """
        conn = _v1_connection()
        ensure_schema(conn)
        ensure_schema(conn) # must not raise second time either

    def test_future_schema_version_raises(self) -> None:
        conn = _v1_connection()
        conn.execute("UPDATE schema_meta SET value = ?", (str(SCHEMA_VERSION + 1),))
        conn.commit()
        with pytest.raises(RuntimeError):
            ensure_schema(conn)

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
