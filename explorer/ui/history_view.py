""" History popup: System -> Body -> Species browsable tree, plus a Cmdr totals summary.
Launched from the compact panel's "History" button. A Toplevel, not a plugin_prefs tab --
prefs' open/close lifecycle doesn't fit a live data browser, and its notebook is too cramped
for a multi-column tree. """
import tkinter as tk
import sqlite3

import explorer.utils.th as th
from explorer.utils.treeviewplus import TreeviewPlus
from explorer.utils.misc import hfplus

from explorer.db.store import ExplorerStore
from explorer.state import ExplorerState

def _credits(value:int|None) -> str:
    return hfplus((value, 'num', '-', ''))

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

        self.window = th.TopLevel(self.parent)
        self.window.title("ExplorerLite — History")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        content:th.Frame = th.Frame(self.window) # type: ignore[arg-type] -- a Toplevel is a valid Tk master even though th.Frame's hint says tk.Widget
        content.pack(fill=tk.BOTH, expand=True)

        self.summary_label = th.Label(content, text="", justify=tk.LEFT)
        self.summary_label.pack(fill=tk.X, padx=4, pady=4)

        self.tree = TreeviewPlus(content, columns=("status", "est_value", "actual_value"), show="tree headings")
        self.tree.heading("#0", text="Name")
        self.tree.heading("status", text="Status")
        self.tree.heading("est_value", text="Est. Value", sort_by="num")
        self.tree.heading("actual_value", text="Actual Value", sort_by="num")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.refresh()

    def _on_close(self) -> None:
        if self.window is not None:
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
            f"Cartography — sold: {_credits(cart_sold)} Cr, pending: {_credits(cart_pending)} Cr\n"
            f"Exobiology — sold: {_credits(exo_sold)} Cr, pending: {_credits(exo_pending)} Cr"
        ))

        for item in self.tree.get_children():
            self.tree.delete(item)

        for system in self.store.get_history_tree(self.state.cmdr_id):
            system_iid:str = self.tree.insert(
                "", "end", text=system["name"],
                values=(system["status"], _credits(system["est_value"]), _credits(system["actual_value"])),
            )
            for body in system["children"]:
                body_iid:str = self.tree.insert(
                    system_iid, "end", text=body["name"],
                    values=(body["status"], _credits(body["est_value"]), _credits(body["actual_value"])),
                )
                for species in body["children"]:
                    self.tree.insert(
                        body_iid, "end", text=species["name"],
                        values=(species["status"], _credits(species["est_value"]), _credits(species["actual_value"])),
                    )
