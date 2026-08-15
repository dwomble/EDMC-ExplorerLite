import semantic_version # type: ignore

PLUGIN_NAME:str = "ExplorerLite"
PLUGIN_VERSION:semantic_version.Version = semantic_version.Version.coerce("0.1.0-dev")
VERSION:str = str(PLUGIN_VERSION) # For compatability with the EDMC Plugin Registry

GH_OWNER:str = "dwomble" # Github owner/org
GH_PROJECT:str = "EDMC-ExplorerLite" # Github project name

CONFIG_PREFIX:str = "EDMCExplorerLite_"

# Config keys (all prefixed to stay unique among EDMC's shared config namespace)
CFG_SCAN_VALUE_THRESHOLD:str = f"{CONFIG_PREFIX}ScanValueThreshold"
CFG_EXOBIO_VALUE_THRESHOLD:str = f"{CONFIG_PREFIX}ExobioValueThreshold"
CFG_OVERLAY_ENABLED:str = f"{CONFIG_PREFIX}OverlayEnabled"
CFG_OVERLAY_RADAR_ENABLED:str = f"{CONFIG_PREFIX}OverlayRadarEnabled"
CFG_DEV_MODE:str = f"{CONFIG_PREFIX}DevMode"
CFG_VISIBLE_LINES:str = f"{CONFIG_PREFIX}VisibleLines"

# Defaults agreed during requirements gathering (REQUIREMENTS.md), excluding first-discovery bonus
DEFAULT_SCAN_VALUE_THRESHOLD:int = 750_000
DEFAULT_EXOBIO_VALUE_THRESHOLD:int = 5_000_000
DEFAULT_VISIBLE_LINES:int = 5

DB_FILENAME:str = "explorer.sqlite"
