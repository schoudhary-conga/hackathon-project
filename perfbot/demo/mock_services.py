"""Mock services for demo mode — no external dependencies required."""

import random
from src.constants import SERVICE_ALIASES, SERVICE_MAPPINGS

# Simulated data for demo
MOCK_BUILDS = {
    "platform-objectdb-api": ["202605.3.15", "202605.2.12", "202605.1.8"],
    "platform-scheduler-api": ["202605.3.10", "202605.2.7", "202605.1.3"],
    "platform-configuration-mgmt-api": ["202605.2.20", "202605.1.14"],
    "contract-api": ["202605.3.5", "202605.2.18", "202605.1.9"],
    "dc-ui": ["202605.3.22", "202605.2.16"],
}

MOCK_ENDPOINTS = {
    "platform-objectdb-api": [
        "GET /api/v1/objects",
        "POST /api/v1/objects",
        "GET /api/v1/objects/{id}",
        "PUT /api/v1/objects/{id}",
        "DELETE /api/v1/objects/{id}",
        "GET /api/v1/objects/search",
        "POST /api/v1/objects/bulk",
    ],
    "platform-scheduler-api": [
        "GET /api/v1/schedules",
        "POST /api/v1/schedules",
        "GET /api/v1/schedules/{id}",
        "PUT /api/v1/schedules/{id}",
        "DELETE /api/v1/schedules/{id}",
        "POST /api/v1/schedules/{id}/trigger",
    ],
    "platform-configuration-mgmt-api": [
        "GET /api/v1/configurations",
        "POST /api/v1/configurations",
        "GET /api/v1/configurations/{id}",
        "PUT /api/v1/configurations/{id}",
    ],
    "contract-api": [
        "GET /api/v1/contracts",
        "POST /api/v1/contracts",
        "GET /api/v1/contracts/{id}",
        "PUT /api/v1/contracts/{id}",
        "POST /api/v1/contracts/{id}/activate",
        "POST /api/v1/contracts/{id}/amend",
    ],
    "dc-ui": [
        "navigateToHomePage",
        "loginFlow",
        "searchProducts",
        "addToCart",
        "checkoutFlow",
        "orderConfirmation",
    ],
}


def _generate_mock_p95(base: float = 350.0, variance: float = 200.0) -> float:
    """Generate a realistic p95 value."""
    return round(base + random.uniform(-variance * 0.3, variance), 1)


def _generate_mock_metrics(service: str, seed: int = 0) -> dict:
    """Generate realistic mock metrics for a service."""
    random.seed(seed)
    endpoints = MOCK_ENDPOINTS.get(service, ["GET /api/v1/resource", "POST /api/v1/resource"])
    ep_metrics = {}
    max_p95 = 0.0

    for ep in endpoints:
        val = _generate_mock_p95()
        ep_metrics[ep] = val
        max_p95 = max(max_p95, val)

    return {
        "p95_overall": max_p95,
        "total_requests": random.randint(5000, 50000),
        "error_rate": round(random.uniform(0, 0.02), 4),
        "endpoints": ep_metrics,
    }


class MockAIBrain:
    """Smart intent parser using pattern matching (no Azure OpenAI needed)."""

    # Intent patterns: ordered list of (intent_type, keywords/phrases)
    _INTENT_RULES = [
        # Active runs detection
        ("active_runs", [
            "running", "active", "in progress", "executing", "ongoing",
            "anything running", "any test running", "what's running",
            "is there a test", "current run", "live test",
        ]),
        # Grafana link
        ("grafana_link", [
            "grafana", "dashboard", "link", "open dashboard", "show graph",
            "visualize", "chart",
        ]),
        # Comparison
        ("comparison", [
            "compare", " vs ", "versus", "comparison", "diff between",
            "difference between", "build over build", "last two runs",
            "compare runs", "against", "compared to",
        ]),
        # Regressions
        ("regressions", [
            "regress", "degraded", "worse", "slower", "got worse",
            "performance drop", "degradation", "went down", "increased latency",
            "what broke", "what changed", "any issues", "problems",
        ]),
        # SLA check
        ("sla_check", [
            "sla", "threshold", "within limit", "within sla", "breach",
            "compliance", "meeting sla", "under threshold", "acceptable",
        ]),
        # Drill down (per-API)
        ("drill_down", [
            "drill", "per-api", "per api", "slowest", "which api",
            "endpoints", "breakdown", "detailed", "each api",
            "individual api", "top 5", "worst", "bottleneck",
            "which endpoint", "api level", "per endpoint", "p95 for each",
            "per transaction", "transaction level",
        ]),
        # Pass/fail
        ("pass_fail", [
            "pass", "fail", "did it pass", "health", "status",
            "how did", "how was", "how is", "result", "outcome",
            "went well", "successful", "ok?", "okay?", "good?",
        ]),
        # All services scan
        ("all_services_scan", [
            "all services", "any failures", "everything", "overall health",
            "all tests", "summary of all", "across all", "full report",
        ]),
        # Test details
        ("test_details", [
            "test details", "execution details", "test config", "test configuration",
            "how many vus", "how many users", "duration", "ramp up",
            "test setup", "run config", "run details", "scenario config",
        ]),
    ]

    async def parse_intent(self, user_message: str) -> dict:
        """Parse user message into structured intent using smart pattern matching."""
        text = user_message.lower().strip()

        # Determine intent by checking patterns in priority order
        intent_type = self._match_intent(text)

        # Resolve service name
        service = self._resolve_service(text)

        # If no specific intent matched but we have a service, default to quick_status
        if not intent_type:
            intent_type = "quick_status"

        return {
            "intent": intent_type,
            "service": service,
            "build_id": None,
            "compare_build_id": None,
            "raw_query": user_message,
        }

    def _match_intent(self, text: str) -> str | None:
        """Match text against intent rules."""
        for intent_type, patterns in self._INTENT_RULES:
            for pattern in patterns:
                if pattern in text:
                    return intent_type
        return None

    async def generate_insight(self, metrics: dict, comparison: dict | None = None) -> str:
        """Generate a human-readable insight from metrics data."""
        if comparison:
            verdict = comparison.get("overall_verdict", "PASS")
            breaches = comparison.get("breaches", [])
            improvements = comparison.get("improvements", [])
            if verdict == "FAIL":
                return (
                    f"⚠️ Performance degradation detected — {len(breaches)} endpoint(s) breached SLA. "
                    f"Recommend investigating: {', '.join(breaches[:3])}."
                )
            elif verdict == "WARN":
                return "⚡ Minor regressions detected (>10% delta) but within SLA. Monitor on next run."
            elif improvements:
                return f"✅ All endpoints within SLA. {len(improvements)} endpoint(s) improved vs baseline."
            else:
                return "✅ All endpoints performing within acceptable thresholds. No action needed."
        else:
            p95 = metrics.get("p95_overall", 0)
            endpoints = metrics.get("endpoints", {})
            if p95 > 2000:
                return f"⚠️ Overall p95 is {p95:.0f}ms — exceeds 2000ms threshold. Investigation recommended."
            elif p95 > 1000:
                return f"⚡ Overall p95 is {p95:.0f}ms — approaching threshold. {len(endpoints)} endpoints measured."
            return f"✅ Overall p95 is {p95:.0f}ms — within acceptable range. {len(endpoints)} endpoints measured."

    def _resolve_service(self, text: str) -> str | None:
        """Resolve service name from text using fuzzy matching."""
        # 1. Exact alias match
        for alias, test_name in SERVICE_ALIASES.items():
            if alias in text:
                return test_name
        # 2. Exact service name match
        for name, test_name in SERVICE_MAPPINGS.items():
            if name in text:
                return test_name
        # 3. Partial/fuzzy: split service names on '-' and match fragments
        words = text.split()
        for name, test_name in SERVICE_MAPPINGS.items():
            parts = name.split("-")
            # If any 2+ adjacent parts match words in the query
            for i in range(len(parts)):
                for j in range(i + 1, len(parts) + 1):
                    fragment = " ".join(parts[i:j])
                    if fragment in text and len(fragment) > 3:
                        return test_name
        return None


class MockInfluxDBClient:
    """Mock InfluxDB client returning simulated data."""

    async def get_latest_build_ids(self, test_name: str, count: int = 2) -> list[str]:
        """Return mock build IDs."""
        builds = MOCK_BUILDS.get(test_name, ["202605.1.1", "202604.3.20"])
        return builds[:count]

    async def get_run_summary(self, test_name: str, build_id: str) -> dict:
        """Return mock run summary."""
        # Use build_id as seed for consistent results per build
        seed = hash(f"{test_name}:{build_id}") % 10000
        return _generate_mock_metrics(test_name, seed)

    async def get_per_api_metrics(self, test_name: str, build_id: str) -> list[dict]:
        """Return mock per-API metrics."""
        seed = hash(f"{test_name}:{build_id}") % 10000
        random.seed(seed)
        endpoints = MOCK_ENDPOINTS.get(test_name, ["GET /api/v1/resource"])
        return [
            {
                "name": ep,
                "endpoint": ep,
                "_value": _generate_mock_p95(),
                "current_p95": _generate_mock_p95(),
                "verdict": random.choice(["PASS", "PASS", "PASS", "WARN"]),
            }
            for ep in endpoints
        ]

    async def get_run_time_range(self, test_name: str, build_id: str) -> tuple[int, int]:
        """Return mock time range (now - 2h to now - 30min)."""
        import time
        now = int(time.time() * 1000)
        return now - 7200000, now - 1800000

    async def check_active_runs(self) -> list[dict]:
        """Return mock active runs."""
        return [
            {"testName": "platform-objectdb-api", "buildId": "202605.3.15"},
        ]
