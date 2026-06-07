"""Constants for the RejseplanAPI integration."""

DOMAIN = "rejseplan"

# Update interval in seconds
DEFAULT_SCAN_INTERVAL = 30

# Default walk time in minutes
DEFAULT_WALK_TIME = 5

# Config entry keys
CONF_API_URL = "api_url"
CONF_STOP_ID = "stop_id"
CONF_STOP_NAME = "stop_name"
CONF_LINE_FILTER = "line_filter"
CONF_WALK_TIME = "walk_time"

# API paths
API_PATH_DEPARTURES = "/api/departures/{stop_id}"
API_PATH_STOPS_SEARCH = "/api/stops/search"

# Platforms
PLATFORMS = ["sensor", "binary_sensor"]
