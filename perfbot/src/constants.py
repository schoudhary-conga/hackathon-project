"""Known service name → InfluxDB testName mappings."""

# Folder/alias → actual testName tag in InfluxDB
SERVICE_MAPPINGS: dict[str, str] = {
    "platform-data-api": "platform-objectdb-api",
    "platform-objectdb-api": "platform-objectdb-api",
    "platform-scheduler-api": "platform-scheduler-api",
    "platform-configuration-mgmt-api": "platform-configuration-mgmt-api",
    "contract-api": "contract-api",
    "dc-ui": "dc-ui",
    "partner-commerce": "dc-ui",
    "cart-persona": "cart-persona",
    "platformcomposer-web": "platformcomposer-web",
    "newdocgen-services": "newdocgen-services",
}

# Fuzzy aliases for LLM resolution
SERVICE_ALIASES: dict[str, str] = {
    "platform data": "platform-objectdb-api",
    "pda": "platform-objectdb-api",
    "objectdb": "platform-objectdb-api",
    "scheduler": "platform-scheduler-api",
    "config management": "platform-configuration-mgmt-api",
    "config mgmt": "platform-configuration-mgmt-api",
    "dc ui": "dc-ui",
    "dcui": "dc-ui",
    "contract": "contract-api",
    "cart": "cart-persona",
    "composer": "platformcomposer-web",
    "docgen": "newdocgen-services",
}

# Setup calls to exclude from per-API metrics
EXCLUDED_METRICS = ["getBuildId", "generateClientCredentialsToken"]

# Default SLA thresholds (ms) - p95
DEFAULT_THRESHOLDS: dict[str, float] = {
    "http_req_duration_p95": 2000.0,
    "http_req_duration_p90": 1500.0,
    "http_req_failed_rate": 0.01,  # 1%
}
