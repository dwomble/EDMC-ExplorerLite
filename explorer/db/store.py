"""
ExplorerStore: the plugin's single SQLite connection plus per-Cmdr upserts and the query
helpers the UI needs. See db/schema.py for the table layout.
"""
import sqlite3
from pathlib import Path
from typing import Optional

from config import config # type: ignore

from explorer.constants import DB_FILENAME, GH_PROJECT
from explorer.db.schema import ensure_schema

def _species_status(row:sqlite3.Row) -> str:
    if row["sold"]:
        return "sold"
    if row["lost_at"]:
        return "lost"
    if row["completed_at"]:
        return "done"
    return f"{row['samples_taken']}/3"

def resolve_db_path() -> Path:
    """ Under config.app_dir_path, not plugin_dir -- a manual reinstall wipes plugin_dir outright. """
    directory:Path = Path(config.app_dir_path) / GH_PROJECT
    directory.mkdir(parents=True, exist_ok=True)
    return directory / DB_FILENAME

class ExplorerStore:
    def __init__(self, db_path:Optional[Path] = None) -> None:
        self.db_path:Path = db_path or resolve_db_path()
        self.conn:sqlite3.Connection = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        ensure_schema(self.conn)

    def close(self) -> None:
        self.conn.close()

    def _update(self, table:str, pk:int, **fields) -> None:
        if not fields:
            return
        cols:str = ", ".join(f"{k} = ?" for k in fields)
        values:list = list(fields.values()) + [pk]
        self.conn.execute(f"UPDATE {table} SET {cols} WHERE id = ?", values)
        self.conn.commit()

    # -- Cmdrs --

    def get_or_create_cmdr(self, name:str, fid:str = "") -> int:
        row:sqlite3.Row|None = self.conn.execute("SELECT id FROM cmdrs WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur:sqlite3.Cursor = self.conn.execute("INSERT INTO cmdrs (name, fid) VALUES (?, ?)", (name, fid))
        self.conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid

    def get_cmdr_totals(self, cmdr_id:int) -> sqlite3.Row|None:
        return self.conn.execute(
            "SELECT actual_cartography_credits, actual_exobiology_credits FROM cmdrs WHERE id = ?", (cmdr_id,)
        ).fetchone()

    def get_pending_cartography_value(self, cmdr_id:int) -> int:
        """ Estimated value of bodies whose system isn't sold/lost yet -- an approximation,
        distinct from actual_cartography_credits (ground truth from real sales). """
        row:sqlite3.Row = self.conn.execute(
            """SELECT COALESCE(SUM(COALESCE(bodies.estimated_scan_value, 0) + COALESCE(bodies.estimated_mapping_value, 0)), 0) AS total
               FROM bodies JOIN systems ON systems.id = bodies.system_id
               WHERE bodies.cmdr_id = ? AND systems.sold_at IS NULL AND systems.lost_at IS NULL""",
            (cmdr_id,),
        ).fetchone()
        return row["total"]

    def get_pending_exobiology_value(self, cmdr_id:int) -> int:
        """ Confirmed value of completed-but-unsold-and-not-lost species samples -- "currently
        held" exobiology data ready to sell, distinct from actual_exobiology_credits (ground
        truth from real sales). Matches the same held/unsold/not-lost definition used by
        mark_all_completed_species_sold()/mark_all_unsold_species_progress_lost(). """
        row:sqlite3.Row = self.conn.execute(
            """SELECT COALESCE(SUM(species_progress.confirmed_value), 0) AS total FROM species_progress
               JOIN bodies ON bodies.id = species_progress.body_id
               WHERE bodies.cmdr_id = ? AND species_progress.completed_at IS NOT NULL
                 AND species_progress.sold = 0 AND species_progress.lost_at IS NULL""",
            (cmdr_id,),
        ).fetchone()
        return row["total"]

    # -- Systems --

    def get_or_create_system(self, cmdr_id:int, system_address:int, name:str) -> int:
        row:sqlite3.Row|None = self.conn.execute(
            "SELECT id FROM systems WHERE cmdr_id = ? AND system_address = ?", (cmdr_id, system_address)
        ).fetchone()
        if row:
            return row["id"]
        cur:sqlite3.Cursor = self.conn.execute(
            "INSERT INTO systems (cmdr_id, system_address, name, visited_at) VALUES (?, ?, ?, datetime('now'))",
            (cmdr_id, system_address, name),
        )
        self.conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid

    def get_system(self, system_id:int) -> sqlite3.Row|None:
        return self.conn.execute("SELECT * FROM systems WHERE id = ?", (system_id,)).fetchone()

    def update_system(self, system_id:int, **fields) -> None:
        self._update("systems", system_id, **fields)

    def mark_system_sold(self, cmdr_id:int, system_name:str, timestamp:str) -> None:
        self.conn.execute(
            "UPDATE systems SET sold_at = ? WHERE cmdr_id = ? AND name = ? AND sold_at IS NULL",
            (timestamp, cmdr_id, system_name),
        )
        self.conn.commit()

    def mark_all_unsold_systems_lost(self, cmdr_id:int, timestamp:str) -> None:
        """ Ship destroyed -- any cartography data still held (never sold) across every system
        this Cmdr has visited is gone, not just the current one. """
        self.conn.execute(
            "UPDATE systems SET lost_at = ? WHERE cmdr_id = ? AND sold_at IS NULL AND lost_at IS NULL",
            (timestamp, cmdr_id),
        )
        self.conn.commit()

    # -- Bodies --

    def get_or_create_body(self, cmdr_id:int, system_id:int, body_id:int, body_name:str, body_type:str = "") -> int:
        row:sqlite3.Row|None = self.conn.execute(
            "SELECT id FROM bodies WHERE cmdr_id = ? AND system_id = ? AND body_id = ?",
            (cmdr_id, system_id, body_id),
        ).fetchone()

        if row: return row["id"]

        cur:sqlite3.Cursor = self.conn.execute(
            "INSERT INTO bodies (cmdr_id, system_id, body_id, body_name, body_type) VALUES (?, ?, ?, ?, ?)",
            (cmdr_id, system_id, body_id, body_name, body_type),
        )
        self.conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid

    def get_body(self, body_pk:int) -> sqlite3.Row|None:
        return self.conn.execute("SELECT * FROM bodies WHERE id = ?", (body_pk,)).fetchone()

    def update_body(self, body_pk:int, **fields) -> None:
        self._update("bodies", body_pk, **fields)

    def get_flagged_bodies_for_system(self, system_id:int) -> list[sqlite3.Row]:
        """ `has_prediction` distinguishes a genuine Scan-based genus guess from a body that's
        only here because FSSBodySignals already confirmed biology (no guess needed/available). """
        return self.conn.execute(
            """SELECT *, EXISTS (SELECT 1 FROM genus_predictions gp WHERE gp.body_id = bodies.id) AS has_prediction
               FROM bodies WHERE system_id = ? AND (has_biological_signals IS NOT 0) AND (
                   flagged_value = 1 OR flagged_exobio = 1 OR has_biological_signals = 1 OR
                   EXISTS (SELECT 1 FROM genus_predictions gp WHERE gp.body_id = bodies.id)
               ) ORDER BY body_id""",
            (system_id,),
        ).fetchall()

    # -- Genus predictions (pre-DSS, from Scan properties) --

    def replace_genus_predictions(self, body_pk:int, predictions:list[tuple[str, str|None, float]]) -> None:
        """ Full replace, not merge -- predictions are always a fresh recompute from the latest
        Scan. `species` is None for a genus-only guess (no species-level ruleset data for that
        genus -- see valuation/species_conditions.py). """
        self.conn.execute("DELETE FROM genus_predictions WHERE body_id = ?", (body_pk,))
        self.conn.executemany(
            "INSERT INTO genus_predictions (body_id, genus, species, confidence) VALUES (?, ?, ?, ?)",
            [(body_pk, genus, species, confidence) for genus, species, confidence in predictions],
        )
        self.conn.commit()

    def get_genus_predictions_for_body(self, body_pk:int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM genus_predictions WHERE body_id = ? ORDER BY confidence DESC", (body_pk,)
        ).fetchall()

    # -- Body genuses (pre/post-DSS biological signal genus hints) --

    def upsert_body_genus(self, body_pk:int, genus:str, signal_count:int|None, revealed_by:str) -> None:
        self.conn.execute(
            """INSERT INTO body_genuses (body_id, genus, signal_count, revealed_by) VALUES (?, ?, ?, ?)
               ON CONFLICT(body_id, genus) DO UPDATE SET signal_count = excluded.signal_count, revealed_by = excluded.revealed_by""",
            (body_pk, genus, signal_count, revealed_by),
        )
        self.conn.commit()

    def get_body_genuses(self, body_pk:int) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM body_genuses WHERE body_id = ?", (body_pk,)).fetchall()

    # -- Exobiology sample progress --

    def get_or_create_species_progress(self, body_pk:int, genus:str) -> int:
        row:sqlite3.Row|None = self.conn.execute(
            "SELECT id FROM species_progress WHERE body_id = ? AND genus = ?", (body_pk, genus)
        ).fetchone()

        if row: return row["id"]

        cur:sqlite3.Cursor = self.conn.execute("INSERT INTO species_progress (body_id, genus) VALUES (?, ?)", (body_pk, genus))
        self.conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid

    def update_species_progress(self, progress_id:int, **fields) -> None:
        self._update("species_progress", progress_id, **fields)

    def get_species_progress_row(self, progress_id:int) -> sqlite3.Row|None:
        return self.conn.execute("SELECT * FROM species_progress WHERE id = ?", (progress_id,)).fetchone()

    def mark_all_completed_species_sold(self, cmdr_id:int) -> None:
        """ Presume every completed-but-unsold sample was sold -- SellOrganicData's BioData
        doesn't reliably itemize what actually got sold for how much (e.g. a "sell all" at
        Vista Genomics), so there's nothing reliable to match against. Uses each sample's own
        confirmed value (from ScanOrganic) as its sold value. """

        rows:list[sqlite3.Row] = self.conn.execute(
            """SELECT species_progress.id, species_progress.confirmed_value FROM species_progress
               JOIN bodies ON bodies.id = species_progress.body_id
               WHERE bodies.cmdr_id = ? AND species_progress.completed_at IS NOT NULL AND species_progress.sold = 0""",
            (cmdr_id,),
        ).fetchall()

        self.conn.executemany(
            "UPDATE species_progress SET sold = 1, sold_value = ? WHERE id = ?",
            [(row["confirmed_value"] or 0, row["id"]) for row in rows],
        )
        self.conn.commit()

    def mark_all_unsold_species_progress_lost(self, cmdr_id:int, timestamp:str) -> None:
        """ Ship destroyed -- any completed exobiology sample data still held (never sold) is
        gone. Only completed rows count as "data" to lose (matches what SellOrganicData would
        ever have sold); in-progress sampling isn't registered as data yet. """

        self.conn.execute(
            """UPDATE species_progress SET lost_at = ?
               WHERE lost_at IS NULL AND sold = 0 AND completed_at IS NOT NULL AND body_id IN (
                   SELECT id FROM bodies WHERE cmdr_id = ?
               )""",
            (timestamp, cmdr_id),
        )
        self.conn.commit()

    def get_species_progress_for_body(self, body_pk:int) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM species_progress WHERE body_id = ?", (body_pk,)).fetchall()

    # -- Sales (ground truth) --

    def get_history_tree(self, cmdr_id:int) -> list[dict]:
        """ Nested System -> Body -> Species structure for the history view. Cartography value
        isn't attributable per-system/body (only species-level sold_value is real); est. values are best-effort. """
        systems:list[sqlite3.Row] = self.conn.execute("SELECT * FROM systems WHERE cmdr_id = ? ORDER BY visited_at", (cmdr_id,)).fetchall()

        tree:list[dict] = []
        for system in systems:
            bodies:list[sqlite3.Row] = self.conn.execute("SELECT * FROM bodies WHERE system_id = ? ORDER BY body_id", (system["id"],)).fetchall()

            body_nodes:list[dict] = []
            system_est_total:int = 0
            for body in bodies:
                species_nodes:list[dict] = [
                    {
                        "name": row["species"] or f"{row['genus']} sp.",
                        "status": _species_status(row),
                        "est_value": row["confirmed_value"] or 0,
                        "actual_value": row["sold_value"] or 0,
                    }
                    for row in self.get_species_progress_for_body(body["id"])
                ]
                body_est:int = max(body["estimated_scan_value"] or 0, body["estimated_mapping_value"] or 0)
                system_est_total += body_est

                body_nodes.append({
                    "name": body["body_name"],
                    "status": "mapped" if body["mapped_at"] else ("scanned" if body["scanned_at"] else "unscanned"),
                    "est_value": body_est,
                    "actual_value": 0,
                    "children": species_nodes,
                })

            tree.append({
                "name": system["name"],
                "status": "sold" if system["sold_at"] else ("lost" if system["lost_at"] else "unsold"),
                "est_value": system_est_total,
                "actual_value": 0,
                "children": body_nodes,
            })

        return tree

    def record_sale(self, cmdr_id:int, event_type:str, timestamp:str, system_name:str|None, total_value:int, raw_json:str) -> None:
        self.conn.execute(
            "INSERT INTO sale_events (cmdr_id, event_type, timestamp, system_name, total_value, raw_json) VALUES (?, ?, ?, ?, ?, ?)",
            (cmdr_id, event_type, timestamp, system_name, total_value, raw_json),
        )
        column:str = "actual_cartography_credits" if event_type == "cartography" else "actual_exobiology_credits"
        self.conn.execute(f"UPDATE cmdrs SET {column} = {column} + ? WHERE id = ?", (total_value, cmdr_id))
        self.conn.commit()
