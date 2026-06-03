"""PerfBot Demo Chat App — standalone web UI for demonstrating the bot logic."""

import json
import os
import sys

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

# Ensure K6 env vars map to INFLUXDB_ vars for the demo
if not os.environ.get("INFLUXDB_TOKEN") and os.environ.get("K6_INFLUXDB_TOKEN"):
    os.environ["INFLUXDB_TOKEN"] = os.environ["K6_INFLUXDB_TOKEN"]

# Ensure perfbot root is on path regardless of where script is invoked from
_PERFBOT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PERFBOT_ROOT not in sys.path:
    sys.path.insert(0, _PERFBOT_ROOT)
_DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
if _DEMO_DIR not in sys.path:
    sys.path.insert(0, _DEMO_DIR)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from mock_services import MockAIBrain, MockInfluxDBClient
from src.comparison import compare_runs, check_sla, find_regressions, find_slowest_endpoints
from src.charts import generate_comparison_chart
from src.grafana import build_grafana_url
from src.constants import SERVICE_MAPPINGS, SERVICE_ALIASES

app = FastAPI(title="PerfBot Demo Chat")

# Toggle: set env var USE_REAL_INFLUXDB=false to use mock data (defaults to true/real InfluxDB)
USE_REAL_INFLUXDB = os.environ.get("USE_REAL_INFLUXDB", "true").lower() not in ("false", "0", "no")

# Toggle: set env var USE_REAL_AI=false to disable LLM intent parsing (defaults to true/Ollama)
USE_REAL_AI = os.environ.get("USE_REAL_AI", "true").lower() not in ("false", "0", "no")

if USE_REAL_AI:
    from src.ai_brain import ai_brain
    print("[INFO] Using REAL AI brain (Ollama llama3.1) for intent parsing")
else:
    ai_brain = MockAIBrain()
    print("[INFO] Using MOCK AI brain (keyword matching)")

if USE_REAL_INFLUXDB:
    from src.influxdb_client import influxdb_client
    print("[INFO] Using REAL InfluxDB client (ensure INFLUXDB_TOKEN is set)")
else:
    influxdb_client = MockInfluxDBClient()
    print("[INFO] Using MOCK data (set USE_REAL_INFLUXDB=true for real InfluxDB)")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the chat UI."""
    html_path = os.path.join(_DEMO_DIR, "static", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/chat")
async def chat(request: Request):
    """Process a user message and return a response."""
    body = await request.json()
    user_message = body.get("message", "").strip()

    if not user_message:
        return JSONResponse({"response": _build_welcome_response()})

    # Parse intent
    intent = await ai_brain.parse_intent(user_message)

    # Handle the intent
    result = await _handle_intent(intent)

    return JSONResponse({"response": result})


@app.get("/api/services")
async def list_services():
    """Return available services for autocomplete."""
    services = list(set(SERVICE_MAPPINGS.values()))
    return JSONResponse({"services": sorted(services)})


async def _handle_intent(intent: dict) -> dict:
    """Route intent to handler and return structured response."""
    intent_type = intent.get("intent", "quick_status")
    service = intent.get("service")

    response_style = intent.get("response_style", "detailed")

    try:
        if intent_type == "general_info":
            return await _handle_general_info(intent.get("raw_query", ""))
        elif intent_type == "active_runs":
            return await _handle_active_runs()
        elif intent_type == "grafana_link":
            return await _handle_grafana_link(service, intent.get("build_id"))
        elif not service:
            return {
                "type": "error",
                "message": "I couldn't determine which service you're asking about. "
                           "Try: 'How did platform-data-api do in the last run?'",
            }
        elif response_style == "brief":
            return await _handle_brief_response(intent_type, service, intent)
        elif intent_type in ("quick_status", "pass_fail"):
            return await _handle_quick_status(service, intent.get("build_id"))
        elif intent_type == "drill_down":
            return await _handle_drill_down(service, intent.get("build_id"))
        elif intent_type == "comparison":
            return await _handle_comparison(service, intent.get("build_id"), intent.get("compare_build_id"))
        elif intent_type == "regressions":
            return await _handle_regressions(service, intent.get("build_id"))
        elif intent_type == "sla_check":
            return await _handle_sla_check(service, intent.get("build_id"))
        elif intent_type == "test_details":
            return await _handle_test_details(service, intent.get("build_id"))
        else:
            return await _handle_quick_status(service, intent.get("build_id"))
    except Exception as e:
        return {"type": "error", "message": f"Error processing request: {str(e)}"}


async def _handle_quick_status(service: str, build_id: str | None) -> dict:
    """Handle quick status queries."""
    build_ids = await influxdb_client.get_latest_build_ids(service, count=2)
    if not build_ids:
        return {"type": "error", "message": f"No runs found for {service} in the last 30 days."}

    current_id = build_id or build_ids[0]
    baseline_id = build_ids[1] if len(build_ids) > 1 else None

    current_metrics = await influxdb_client.get_run_summary(service, current_id)

    if baseline_id:
        baseline_metrics = await influxdb_client.get_run_summary(service, baseline_id)
        comparison = compare_runs(current_metrics, baseline_metrics)
    else:
        comparison = {
            "overall_verdict": "PASS" if current_metrics.get("p95_overall", 0) < 2000 else "WARN",
            "metrics": [],
            "breaches": [],
        }

    chart_b64 = generate_comparison_chart(comparison) if baseline_id else ""
    insight = await ai_brain.generate_insight(current_metrics, comparison if baseline_id else None)

    start_ms, end_ms = await influxdb_client.get_run_time_range(service, current_id)
    grafana_url = build_grafana_url(service, current_id, start_ms, end_ms)

    return {
        "type": "run_summary",
        "service": service,
        "build_id": current_id,
        "baseline_id": baseline_id or "N/A",
        "comparison": comparison,
        "chart_base64": chart_b64,
        "insight": insight,
        "grafana_url": grafana_url,
    }


async def _handle_drill_down(service: str, build_id: str | None) -> dict:
    """Handle per-API drill-down."""
    if not build_id:
        build_ids = await influxdb_client.get_latest_build_ids(service, count=1)
        build_id = build_ids[0] if build_ids else None

    if not build_id:
        return {"type": "error", "message": f"No runs found for {service}."}

    per_api = await influxdb_client.get_per_api_metrics(service, build_id)
    return {
        "type": "per_api",
        "service": service,
        "build_id": build_id,
        "metrics": per_api,
    }


async def _handle_comparison(service: str, build_a: str | None, build_b: str | None) -> dict:
    """Handle explicit build comparison."""
    build_ids = await influxdb_client.get_latest_build_ids(service, count=2)
    if len(build_ids) < 2:
        return {"type": "error", "message": f"Need at least 2 runs to compare. Found {len(build_ids)}."}

    build_a = build_a or build_ids[0]
    build_b = build_b or build_ids[1]

    current = await influxdb_client.get_run_summary(service, build_a)
    baseline = await influxdb_client.get_run_summary(service, build_b)
    comparison = compare_runs(current, baseline)
    chart_b64 = generate_comparison_chart(comparison)
    insight = await ai_brain.generate_insight(current, comparison)

    start_ms, end_ms = await influxdb_client.get_run_time_range(service, build_a)
    grafana_url = build_grafana_url(service, build_a, start_ms, end_ms)

    return {
        "type": "run_summary",
        "service": service,
        "build_id": build_a,
        "baseline_id": build_b,
        "comparison": comparison,
        "chart_base64": chart_b64,
        "insight": insight,
        "grafana_url": grafana_url,
    }


async def _handle_general_info(user_query: str) -> dict:
    """Handle FAQ/general questions without InfluxDB data."""
    response = await ai_brain.client.chat.completions.create(
        model=ai_brain.model,
        messages=[
            {"role": "system", "content": (
                "You are PerfBot, a performance testing assistant. Answer general questions "
                "about the services you monitor, terminology (p95, SLA, etc.), and what you can do. "
                "Keep answers to 2-4 sentences. Be conversational.\n\n"
                "Services you track:\n"
                "- platform-data-api (PDA / objectdb) — platform data service\n"
                "- platform-scheduler-api — job scheduling service\n"
                "- platform-configuration-mgmt-api — config management\n"
                "- contract-api — contract lifecycle service\n"
                "- dc-ui (Partner Commerce) — browser/UI tests\n\n"
                "You can: check pass/fail, show per-API breakdown, compare builds, "
                "detect regressions, check SLA compliance, show Grafana links."
            )},
            {"role": "user", "content": user_query},
        ],
        temperature=0.4,
        max_tokens=200,
    )
    return {"type": "text", "message": response.choices[0].message.content.strip()}


async def _handle_brief_response(intent_type: str, service: str, intent: dict) -> dict:
    """Handle queries that need a concise conversational answer."""
    user_query = intent.get("raw_query", "")

    build_ids = await influxdb_client.get_latest_build_ids(service, count=2)
    if not build_ids:
        return {"type": "text", "message": f"No runs found for **{service}** in the last 30 days."}

    current_id = intent.get("build_id") or build_ids[0]
    current_metrics = await influxdb_client.get_run_summary(service, current_id)

    comparison = None
    if len(build_ids) > 1:
        baseline_metrics = await influxdb_client.get_run_summary(service, build_ids[1])
        comparison = compare_runs(current_metrics, baseline_metrics)

    response_text = await ai_brain.generate_conversational_response(
        user_query, current_metrics, comparison
    )
    return {"type": "text", "message": response_text}


async def _handle_regressions(service: str, build_id: str | None) -> dict:
    """Handle regression queries."""
    build_ids = await influxdb_client.get_latest_build_ids(service, count=2)
    if len(build_ids) < 2:
        return {"type": "error", "message": "Need at least 2 runs to detect regressions."}

    current_id = build_id or build_ids[0]
    baseline_id = build_ids[1]

    current = await influxdb_client.get_run_summary(service, current_id)
    baseline = await influxdb_client.get_run_summary(service, baseline_id)
    comparison = compare_runs(current, baseline)
    regressions = find_regressions(comparison)

    if not regressions:
        return {"type": "info", "message": f"✅ No regressions detected for {service} (threshold: >10% degradation)."}

    return {
        "type": "per_api",
        "service": service,
        "build_id": current_id,
        "metrics": regressions,
    }


async def _handle_sla_check(service: str, build_id: str | None) -> dict:
    """Handle SLA check queries."""
    if not build_id:
        build_ids = await influxdb_client.get_latest_build_ids(service, count=1)
        build_id = build_ids[0] if build_ids else None

    if not build_id:
        return {"type": "error", "message": f"No runs found for {service}."}

    metrics = await influxdb_client.get_run_summary(service, build_id)
    sla_result = check_sla(metrics)

    return {
        "type": "sla_check",
        "service": service,
        "build_id": build_id,
        "sla_result": sla_result,
    }


async def _handle_active_runs() -> dict:
    """Handle active runs query."""
    runs = await influxdb_client.check_active_runs()
    return {
        "type": "active_runs",
        "runs": runs,
    }


async def _handle_test_details(service: str, build_id: str | None) -> dict:
    """Handle test details/configuration queries."""
    if not build_id:
        build_ids = await influxdb_client.get_latest_build_ids(service, count=1)
        build_id = build_ids[0] if build_ids else None

    if not build_id:
        return {"type": "error", "message": f"No runs found for {service}."}

    details = await influxdb_client.get_test_details(service, build_id)
    if not details:
        return {
            "type": "info",
            "message": f"No test details found for {service} (testId: {build_id}). "
                       "The test may not emit the testDetails counter.",
        }

    return {
        "type": "test_details",
        "service": service,
        "build_id": build_id,
        "details": details,
    }


async def _handle_grafana_link(service: str | None, build_id: str | None) -> dict:
    """Handle Grafana link requests."""
    if not service:
        return {"type": "error", "message": "Please specify a service for the Grafana link."}

    if not build_id:
        build_ids = await influxdb_client.get_latest_build_ids(service, count=1)
        build_id = build_ids[0] if build_ids else None

    if not build_id:
        return {"type": "error", "message": f"No runs found for {service}."}

    start_ms, end_ms = await influxdb_client.get_run_time_range(service, build_id)
    url = build_grafana_url(service, build_id, start_ms, end_ms)

    return {
        "type": "grafana_link",
        "service": service,
        "build_id": build_id,
        "url": url,
    }


def _build_welcome_response() -> dict:
    return {
        "type": "welcome",
        "message": (
            "👋 Hi! I'm **PerfBot** — your AI performance insights assistant.\n\n"
            "Try asking:\n"
            "- *How did platform-data-api do in the last run?*\n"
            "- *Did last night's run pass?*\n"
            "- *Which APIs are slowest for scheduler?*\n"
            "- *Compare the last two runs for contract-api*\n"
            "- *Is anything running right now?*\n"
            "- *Show Grafana link for dc-ui*"
        ),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8080)
