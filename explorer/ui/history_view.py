""" History popup: System -> Body -> Species browsable tree, plus a Cmdr totals summary.
Launched from the compact panel's "History" button. A Toplevel, not a plugin_prefs tab --
prefs' open/close lifecycle doesn't fit a live data browser, and its notebook is too cramped
for a multi-column tree. """
import tkinter as tk
from tkinter import ttk
import sqlite3
from typing import Literal

from config import config # type: ignore

from explorer.utils.treeviewplus import TreeviewPlus
from explorer.utils.misc import hfplus

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState
from explorer.constants import CFG_HISTORY_WINDOW_GEOMETRY

def _credits(value:int|None) -> str:
    return hfplus((value, 'num', '-', ''))

def _date_str(iso:str) -> str:
    return iso[:10] if iso else ""

# (column, heading, anchor, width, stretch, sort_by) -- date sorts as plain text ("name"), not
# TreeviewPlus's "datetime" helper, since _date_str's ISO YYYY-MM-DD format already sorts
# chronologically as a string, and the helper's dateutil parse would crash on the blank dates
# shown for rows with no recorded date.
COLUMNS:tuple[tuple[str, str, Literal["w", "e"], int, bool, str|None], ...] = (
    ("status", "Status", "w", 80, False, None),
    ("date", "Date", "w", 90, False, "name"),
    ("cart_est", "Cart. Est.", "e", 90, False, "num"),
    ("cart_actual", "Cart. Actual", "e", 90, False, "num"),
    ("exo_base", "Exo. Base", "e", 90, False, "num"),
    ("exo_full", "Exo. Full", "e", 90, False, "num"),
)

class HistoryView:
    """ Owns the (lazily-created) history Toplevel. Call refresh() after any DB change. """

    def __init__(self, parent:tk.Widget, store:ExplorerStore, state:ExplorerState) -> None:
        self.parent:tk.Widget = parent
        self.store:ExplorerStore = store
        self.state:ExplorerState = state
        self.window:tk.Toplevel|None = None
        self.summary_label:tk.Label|None = None
        self.tree:TreeviewPlus|None = None

    def open(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.refresh()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("ExplorerLite — History")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        saved_geometry:str = config.get_str(CFG_HISTORY_WINDOW_GEOMETRY, default="")
        if saved_geometry:
            self.window.geometry(saved_geometry)

        content:tk.Frame = tk.Frame(self.window) # type: ignore[arg-type] -- a Toplevel is a valid Tk master even though th.Frame's hint says tk.Widget
        content.pack(fill=tk.BOTH, expand=True)

        self.summary_label = tk.Label(content, text="", justify=tk.LEFT)
        self.summary_label.pack(fill=tk.X, padx=4, pady=4)

        tree_frame:tk.Frame = tk.Frame(content)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree = TreeviewPlus(tree_frame, columns=tuple(c[0] for c in COLUMNS), show="tree headings")
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.column("#0", anchor="w", stretch=True, minwidth=140)
        for key, text, anchor, width, stretch, sort_by in COLUMNS:
            self.tree.heading(key, text=text, anchor=anchor, sort_by=sort_by)
            self.tree.column(key, anchor=anchor, width=width, stretch=stretch)
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar:ttk.Scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.refresh()

    def _on_close(self) -> None:
        if self.window is not None:
            config.set(CFG_HISTORY_WINDOW_GEOMETRY, self.window.geometry())
            self.window.destroy()
        self.window = None
        self.summary_label = None
        self.tree = None

    def refresh(self) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        assert self.summary_label is not None and self.tree is not None

        if self.state.cmdr_id is None:
            self.summary_label.configure(text="No Cmdr yet")
            for item in self.tree.get_children():
                self.tree.delete(item)
            return

        totals:sqlite3.Row|None = self.store.get_cmdr_totals(self.state.cmdr_id)
        cart_sold:int = totals["actual_cartography_credits"] if totals else 0
        exo_sold:int = totals["actual_exobiology_credits"] if totals else 0
        cart_pending:int = self.store.get_pending_cartography_value(self.state.cmdr_id)
        exo_pending:int = self.store.get_pending_exobiology_value(self.state.cmdr_id)
        self.summary_label.configure(text=(
            f"Cartography — sold: {_credits(cart_sold)} Cr, pending: {_credits(cart_pending)} Cr   "
            f"Exobiology — sold: {_credits(exo_sold)} Cr, pending: {_credits(exo_pending)} Cr"
        ))

        for item in self.tree.get_children():
            self.tree.delete(item)

        for system in self.store.get_history_tree(self.state.cmdr_id):
            system_iid:str = self.tree.insert("", "end", text=system["name"], values=self._row_values(system))
            for body in system["children"]:
                body_iid:str = self.tree.insert(system_iid, "end", text=body["name"], values=self._row_values(body))
                for species in body["children"]:
                    self.tree.insert(body_iid, "end", text=species["name"], values=self._row_values(species))

    def _row_values(self, node:dict) -> tuple[str, ...]:
        return (
            node["status"].title(), _date_str(node["date"]),
            _credits(node["cart_est"]), _credits(node["cart_actual"]),
            _credits(node["exo_base"]), _credits(node["exo_full"]),
        )
