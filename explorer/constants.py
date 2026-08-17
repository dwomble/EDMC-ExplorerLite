PLUGIN_NAME:str = "ExplorerLite"

GH_OWNER:str = "dwomble" # Github owner/org
GH_PROJECT:str = "EDMC-ExplorerLite" # Github project name

CONFIG_PREFIX:str = "EDMCExplorerLite_"

# Config keys (all prefixed to stay unique among EDMC's shared config namespace)
CFG_PANEL_ENABLED:str = f"{CONFIG_PREFIX}PanelEnabled" # master show/hide -- data collection is unaffected
CFG_SCAN_VALUE_THRESHOLD:str = f"{CONFIG_PREFIX}ScanValueThreshold"
CFG_EXOBIO_VALUE_THRESHOLD:str = f"{CONFIG_PREFIX}ExobioValueThreshold"
CFG_OVERLAY_RADAR_ENABLED:str = f"{CONFIG_PREFIX}OverlayRadarEnabled"
CFG_OVERLAY_SUMMARY_ENABLED:str = f"{CONFIG_PREFIX}OverlaySummaryEnabled"
CFG_OVERLAY_SUMMARY_TEXT_COLOR:str = f"{CONFIG_PREFIX}OverlaySummaryTextColor"
CFG_DEV_MODE:str = f"{CONFIG_PREFIX}DevMode"
CFG_VISIBLE_LINES:str = f"{CONFIG_PREFIX}VisibleLines"
CFG_OVERLAY_RADAR_SIZE:str = f"{CONFIG_PREFIX}OverlayRadarSize"
CFG_HISTORY_WINDOW_GEOMETRY:str = f"{CONFIG_PREFIX}HistoryWindowGeometry"
CFG_HISTORY_UNSOLD_ONLY:str = f"{CONFIG_PREFIX}HistoryUnsoldOnly"
CFG_HISTORY_TIME_RANGE:str = f"{CONFIG_PREFIX}HistoryTimeRange"

# Defaults agreed during requirements gathering (REQUIREMENTS.md), excluding first-discovery bonus
DEFAULT_SCAN_VALUE_THRESHOLD:int = 750_000
DEFAULT_EXOBIO_VALUE_THRESHOLD:int = 5_000_000
DEFAULT_VISIBLE_LINES:int = 5
DEFAULT_OVERLAY_RADAR_SIZE:int = 150 # on-screen pixel radius, matches overlay_frames.py's original hardcoded RADIUS_PX
DEFAULT_OVERLAY_SUMMARY_TEXT_COLOR:str = "#ffffff"
DEFAULT_HISTORY_TIME_RANGE:str = "All time"

DB_FILENAME:str = "explorer.sqlite"
