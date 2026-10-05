from dataclasses import dataclass, fields

from explorer.db.store import ExplorerStore
from explorer.ui.history_view import HistoryView
from explorer.ui.overlay_frames import RadarOverlay
from explorer.ui.overlay_summary import SystemSummaryOverlay
from explorer.ui.panel import ExplorerPanel
from explorer.utils.overlay import Overlay
from explorer.utils.updater import Notices, Updater

@dataclass
class Context:
    """ The runtime objects load.py's EDMC hooks build. Only load.py and tests touch it; everything else is handed what it needs. """
    updater:Updater|None = None
    notices:Notices|None = None
    store:ExplorerStore|None = None
    panel:ExplorerPanel|None = None
    radar:RadarOverlay|None = None
    summary_overlay:SystemSummaryOverlay|None = None
    history_view:HistoryView|None = None
    overlay_backend:Overlay|None = None

    @classmethod
    def reset(cls) -> None:
        for field in fields(cls): setattr(cls, field.name, field.default)
