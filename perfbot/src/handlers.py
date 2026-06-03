"""Intent handler — routes parsed intents to the appropriate logic."""

from src.influxdb_client import influxdb_client
from src.ai_brain import ai_brain
from src.comparison import compare_runs, check_sla, find_regressions, find_slowest_endpoints
from src.charts import generate_comparison_chart
from src.grafana import build_grafana_url
from src.cards import (
    build_run_summary_card,
    build_per_api_card,
    build_error_card,
    build_active_runs_card,
)


async def handle_intent(intent: dict) -> dict | str:
    """Route intent to handler and return an Adaptive Card attachment or a text response."""
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
            return build_error_card(
                "I couldn't determine which service you're asking about. "
                "Try: 'How did platform-data-api do in the last run?'"
            )
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
        elif intent_type == "all_services_scan":
            return await _handle_all_services_scan()
        else:
            return await _handle_quick_status(service, intent.get("build_id"))
    except Exception as e:
        return build_error_card(f"Error processing request: {str(e)}")


async def _handle_general_info(user_query: str) -> str:
    """Handle FAQ/general questions that don't require InfluxDB data."""
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
    return response.choices[0].message.content.strip()


async def _handle_brief_response(intent_type: str, service: str, intent: dict) -> str:
    """Handle queries that need a concise conversational answer instead of full data cards."""
    build_id = intent.get("build_id")
    user_query = intent.get("raw_query", "")

    # Fetch metrics — we still need data, but we'll let the LLM summarize
    build_ids = await influxdb_client.get_latest_build_ids(service, count=2)
    if not build_ids:
        return f"No runs found for **{service}** in the last 30 days."

    current_id = build_id or build_ids[0]
    current_metrics = await influxdb_client.get_run_summary(service, current_id)

    comparison = None
    if len(build_ids) > 1:
        baseline_metrics = await influxdb_client.get_run_summary(service, build_ids[1])
        comparison = compare_runs(current_metrics, baseline_metrics)

    # Generate a direct conversational answer
    response_text = await ai_brain.generate_conversational_response(
        user_query, current_metrics, comparison
    )
    return response_text


async def _handle_quick_status(service: str, build_id: str | None) -> dict:
    """Handle quick status / pass-fail queries."""
    build_ids = await influxdb_client.get_latest_build_ids(service, count=2)
    if not build_ids:
        return build_error_card(f"No runs found for {service} in the last 30 days.")

    current_id = build_id or build_ids[0]
    baseline_id = build_ids[1] if len(build_ids) > 1 else None

    current_metrics = await influxdb_client.get_run_summary(service, current_id)

    if baseline_id:
        baseline_metrics = await influxdb_client.get_run_summary(service, baseline_id)
        comparison = compare_runs(current_metrics, baseline_metrics)
    else:
        comparison = {
            "overall_verdict": "PASS" if current_metrics.get("p95_overall", 0) < 2000 else "WARN",
            "metrics": [
                {"endpoint": ep, "current_p95": val, "baseline_p95": 0, "delta_ms": 0, "delta_pct": 0, "verdict": "PASS"}
                for ep, val in current_metrics.get("endpoints", {}).items()
            ],
            "breaches": [],
        }

    chart_b64 = generate_comparison_chart(comparison) if baseline_id else ""

    insight = await ai_brain.generate_insight(
        current_metrics,
        comparison if baseline_id else None,
    )

    start_ms, end_ms = await influxdb_client.get_run_time_range(service, current_id)
    grafana_url = build_grafana_url(service, current_id, start_ms, end_ms)

    return build_run_summary_card(
        service=service,
        build_id=current_id,
        baseline_id=baseline_id or "N/A",
        comparison=comparison,
        chart_base64=chart_b64,
        insight=insight,
        grafana_url=grafana_url,
    )


async def _handle_drill_down(service: str, build_id: str | None) -> dict:
    """Handle per-API drill-down."""
    if not build_id:
        build_ids = await influxdb_client.get_latest_build_ids(service, count=1)
        build_id = build_ids[0] if build_ids else None

    if not build_id:
        return build_error_card(f"No runs found for {service}.")

    per_api = await influxdb_client.get_per_api_metrics(service, build_id)
    return build_per_api_card(service, build_id, per_api)


async def _handle_comparison(service: str, build_a: str | None, build_b: str | None) -> dict:
    """Handle explicit build comparison."""
    if not build_a or not build_b:
        build_ids = await influxdb_client.get_latest_build_ids(service, count=2)
        if len(build_ids) < 2:
            return build_error_card(f"Need at least 2 runs to compare. Found {len(build_ids)}.")
        build_a = build_a or build_ids[0]
        build_b = build_b or build_ids[1]

    current = await influxdb_client.get_run_summary(service, build_a)
    baseline = await influxdb_client.get_run_summary(service, build_b)
    comparison = compare_runs(current, baseline)
    chart_b64 = generate_comparison_chart(comparison)
    insight = await ai_brain.generate_insight(current, comparison)

    start_ms, end_ms = await influxdb_client.get_run_time_range(service, build_a)
    grafana_url = build_grafana_url(service, build_a, start_ms, end_ms)

    return build_run_summary_card(service, build_a, build_b, comparison, chart_b64, insight, grafana_url)


async def _handle_regressions(service: str, build_id: str | None) -> dict:
    """Handle 'what regressed?' queries."""
    build_ids = await influxdb_client.get_latest_build_ids(service, count=2)
    if len(build_ids) < 2:
        return build_error_card(f"Need at least 2 runs to detect regressions.")

    current_id = build_id or build_ids[0]
    baseline_id = build_ids[1]

    current = await influxdb_client.get_run_summary(service, current_id)
    baseline = await influxdb_client.get_run_summary(service, baseline_id)
    comparison = compare_runs(current, baseline)
    regressions = find_regressions(comparison)

    if not regressions:
        return build_error_card(f"✅ No regressions detected for {service} (threshold: >10% degradation).")

    return build_per_api_card(service, current_id, regressions)


async def _handle_sla_check(service: str, build_id: str | None) -> dict:
    """Handle SLA check queries."""
    if not build_id:
        build_ids = await influxdb_client.get_latest_build_ids(service, count=1)
        build_id = build_ids[0] if build_ids else None

    if not build_id:
        return build_error_card(f"No runs found for {service}.")

    metrics = await influxdb_client.get_run_summary(service, build_id)
    sla_result = check_sla(metrics)

    # Reuse per-API card format for SLA display
    sla_metrics = [
        {"endpoint": c["metric"], "current_p95": c["value"], "verdict": c["status"]}
        for c in sla_result["checks"]
    ]
    return build_per_api_card(service, build_id, sla_metrics)


async def _handle_active_runs() -> dict:
    """Handle 'is anything running?' queries."""
    runs = await influxdb_client.check_active_runs()
    return build_active_runs_card(runs)


async def _handle_grafana_link(service: str | None, build_id: str | None) -> dict:
    """Handle Grafana link requests."""
    if not service:
        return build_error_card("Please specify a service for the Grafana link.")

    if not build_id:
        build_ids = await influxdb_client.get_latest_build_ids(service, count=1)
        build_id = build_ids[0] if build_ids else None

    if not build_id:
        return build_error_card(f"No runs found for {service}.")

    start_ms, end_ms = await influxdb_client.get_run_time_range(service, build_id)
    url = build_grafana_url(service, build_id, start_ms, end_ms)

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": f"📈 Grafana Dashboard: {service}", "size": "Medium", "weight": "Bolder"},
            {"type": "TextBlock", "text": f"Build: {build_id}", "isSubtle": True},
        ],
        "actions": [
            {"type": "Action.OpenUrl", "title": "Open Grafana", "url": url},
        ],
    }
    return {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}


async def _handle_all_services_scan() -> dict:
    """Scan all known services for recent breaches."""
    from src.constants import SERVICE_MAPPINGS

    all_test_names = set(SERVICE_MAPPINGS.values())
    breaches_found = []

    for test_name in all_test_names:
        build_ids = await influxdb_client.get_latest_build_ids(test_name, count=1)
        if not build_ids:
            continue
        metrics = await influxdb_client.get_run_summary(test_name, build_ids[0])
        sla = check_sla(metrics)
        if sla["overall"] == "FAIL":
            breaches_found.append({"service": test_name, "build_id": build_ids[0], "p95": metrics.get("p95_overall", 0)})

    if not breaches_found:
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": [
                {"type": "TextBlock", "text": "✅ All Services Passing", "size": "Large", "weight": "Bolder", "color": "Good"},
                {"type": "TextBlock", "text": "No SLA breaches detected across all monitored services.", "wrap": True},
            ],
        }
    else:
        facts = [{"title": b["service"], "value": f"p95: {b['p95']:.0f}ms (Build: {b['build_id']})"} for b in breaches_found]
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": [
                {"type": "TextBlock", "text": f"⚠️ {len(breaches_found)} Service(s) Breaching SLA", "size": "Large", "weight": "Bolder", "color": "Attention"},
                {"type": "FactSet", "facts": facts},
            ],
        }

    return {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}
