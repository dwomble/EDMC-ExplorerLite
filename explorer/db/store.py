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
    if row["completed_at"]:
        return "done"
    return f"{row['samples_taken']}/3"

def resolve_db_path() -> Path:
    """
    Store under config.app_dir_path (EDMC's persistent app-data directory), namespaced into
    our own subfolder -- not inside the plugin's own code folder (plugin_dir), since a manual
    reinstall (delete-and-reclone) wipes plugin_dir outright and would destroy a Cmdr's entire
    scan history.
    """
    directory = Path(config.app_dir_path) / GH_PROJECT
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
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [pk]
        self.conn.execute(f"UPDATE {table} SET {cols} WHERE id = ?", values)
        self.conn.commit()

    # -- Cmdrs --

    def get_or_create_cmdr(self, name:str, fid:str = "") -> int:
        row = self.conn.execute("SELECT id FROM cmdrs WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute("INSERT INTO cmdrs (name, fid) VALUES (?, ?)", (name, fid))
        self.conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid

    def get_cmdr_totals(self, cmdr_id:int) -> sqlite3.Row|None:
        return self.conn.execute(
            "SELECT actual_cartography_credits, actual_exobiology_credits FROM cmdrs WHERE id = ?", (cmdr_id,)
        ).fetchone()

    # -- Systems --

    def get_or_create_system(self, cmdr_id:int, system_address:int, name:str) -> int:
        row = self.conn.execute(
            "SELECT id FROM systems WHERE cmdr_id = ? AND system_address = ?", (cmdr_id, system_address)
        ).fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute(
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

    # -- Bodies --

    def get_or_create_body(self, cmdr_id:int, system_id:int, body_id:int, body_name:str, body_type:str = "") -> int:
        row = self.conn.execute(
            "SELECT id FROM bodies WHERE cmdr_id = ? AND system_id = ? AND body_id = ?",
            (cmdr_id, system_id, body_id),
        ).fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute(
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
        return self.conn.execute(
            "SELECT * FROM bodies WHERE system_id = ? AND (flagged_value = 1 OR flagged_exobio = 1) ORDER BY body_id",
            (system_id,),
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
        row = self.conn.execute(
            "SELECT id FROM species_progress WHERE body_id = ? AND genus = ?", (body_pk, genus)
        ).fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute("INSERT INTO species_progress (body_id, genus) VALUES (?, ?)", (body_pk, genus))
        self.conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid

    def update_species_progress(self, progress_id:int, **fields) -> None:
        self._update("species_progress", progress_id, **fields)

    def get_species_progress_row(self, progress_id:int) -> sqlite3.Row|None:
        return self.conn.execute("SELECT * FROM species_progress WHERE id = ?", (progress_id,)).fetchone()

    def get_unsold_species_progress(self, cmdr_id:int, genus:str, species:str) -> list[sqlite3.Row]:
        """ Completed, unsold sample rows for a genus+species across this Cmdr's bodies, oldest first (FIFO for best-effort sale attribution). """
        return self.conn.execute(
            """SELECT species_progress.* FROM species_progress
               JOIN bodies ON bodies.id = species_progress.body_id
               WHERE bodies.cmdr_id = ? AND species_progress.genus = ? AND species_progress.species = ?
                 AND species_progress.completed_at IS NOT NULL AND species_progress.sold = 0
               ORDER BY species_progress.completed_at ASC""",
            (cmdr_id, genus, species),
        ).fetchall()

    def get_species_progress_for_body(self, body_pk:int) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM species_progress WHERE body_id = ?", (body_pk,)).fetchall()

    # -- Sales (ground truth) --

    def get_history_tree(self, cmdr_id:int) -> list[dict]:
        """
        Nested System -> Body -> Species structure for the history view. Actual cartography
        value is never attributable per-system/body (MultiSellExplorationData only gives
        system-level totals across a whole transaction) -- only species-level sold_value is
        real. Est. values are best-effort (see valuation/cartography.py's own caveat).
        """
        systems = self.conn.execute("SELECT * FROM systems WHERE cmdr_id = ? ORDER BY visited_at", (cmdr_id,)).fetchall()

        tree = []
        for system in systems:
            bodies = self.conn.execute("SELECT * FROM bodies WHERE system_id = ? ORDER BY body_id", (system["id"],)).fetchall()

            body_nodes = []
            system_est_total = 0
            for body in bodies:
                species_nodes = [
                    {
                        "name": row["species"] or f"{row['genus']} sp.",
                        "status": _species_status(row),
                        "est_value": row["confirmed_value"] or 0,
                        "actual_value": row["sold_value"] or 0,
                    }
                    for row in self.get_species_progress_for_body(body["id"])
                ]
                body_est = max(body["estimated_scan_value"] or 0, body["estimated_mapping_value"] or 0)
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
                "status": "sold" if system["sold_at"] else "unsold",
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
        column = "actual_cartography_credits" if event_type == "cartography" else "actual_exobiology_credits"
        self.conn.execute(f"UPDATE cmdrs SET {column} = {column} + ? WHERE id = ?", (total_value, cmdr_id))
        self.conn.commit()
