"""Adaptive Card builders for Teams bot responses."""


def build_run_summary_card(
    service: str,
    build_id: str,
    baseline_id: str,
    comparison: dict,
    chart_base64: str,
    insight: str,
    grafana_url: str,
) -> dict:
    """Build Adaptive Card for run summary response."""
    verdict = comparison.get("overall_verdict", "PASS")
    verdict_color = _verdict_color(verdict)

    metrics_rows = []
    for m in comparison.get("metrics", [])[:10]:
        emoji = _verdict_emoji(m["verdict"])
        metrics_rows.append({
            "type": "TableRow",
            "cells": [
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": m["endpoint"], "size": "Small"}]},
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": f"{m['baseline_p95']} ms", "size": "Small"}]},
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": f"{m['current_p95']} ms", "size": "Small"}]},
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": f"{m['delta_pct']:+.1f}%", "size": "Small"}]},
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": f"{emoji} {m['verdict']}", "size": "Small"}]},
            ],
        })

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {"type": "TextBlock", "text": f"📊 {service}", "size": "Large", "weight": "Bolder"},
                            {"type": "TextBlock", "text": f"Run: {build_id} vs Baseline: {baseline_id}", "size": "Small", "isSubtle": True},
                        ],
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {"type": "TextBlock", "text": f"{_verdict_emoji(verdict)} {verdict}", "size": "Large", "weight": "Bolder", "color": verdict_color},
                        ],
                    },
                ],
            },
            {"type": "TextBlock", "text": "---", "spacing": "Small"},
            {
                "type": "Table",
                "columns": [
                    {"width": 3},
                    {"width": 1},
                    {"width": 1},
                    {"width": 1},
                    {"width": 1},
                ],
                "firstRowAsHeader": True,
                "rows": [
                    {
                        "type": "TableRow",
                        "cells": [
                            {"type": "TableCell", "items": [{"type": "TextBlock", "text": "Endpoint", "weight": "Bolder", "size": "Small"}]},
                            {"type": "TableCell", "items": [{"type": "TextBlock", "text": "Baseline", "weight": "Bolder", "size": "Small"}]},
                            {"type": "TableCell", "items": [{"type": "TextBlock", "text": "Current", "weight": "Bolder", "size": "Small"}]},
                            {"type": "TableCell", "items": [{"type": "TextBlock", "text": "Delta", "weight": "Bolder", "size": "Small"}]},
                            {"type": "TableCell", "items": [{"type": "TextBlock", "text": "Status", "weight": "Bolder", "size": "Small"}]},
                        ],
                    },
                    *metrics_rows,
                ],
            },
        ],
        "actions": [],
    }

    # Add chart image if available
    if chart_base64:
        card["body"].append({
            "type": "Image",
            "url": f"data:image/png;base64,{chart_base64}",
            "altText": "Performance comparison chart",
            "size": "Large",
        })

    # Add insight
    if insight:
        card["body"].append({
            "type": "TextBlock",
            "text": f"💡 **Insight:** {insight}",
            "wrap": True,
            "spacing": "Medium",
        })

    # Add action buttons
    card["actions"] = [
        {"type": "Action.Submit", "title": "📋 Show Per-API", "data": {"action": "drill_down", "service": service, "build_id": build_id}},
        {"type": "Action.OpenUrl", "title": "📈 Open in Grafana", "url": grafana_url},
    ]

    return {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}


def build_per_api_card(service: str, build_id: str, metrics: list[dict]) -> dict:
    """Build Adaptive Card for per-API drill-down."""
    rows = []
    for m in metrics:
        endpoint = m.get("endpoint") or m.get("name", "unknown")
        p95 = float(m.get("current_p95", m.get("_value", 0)))
        verdict = m.get("verdict", "PASS")
        emoji = _verdict_emoji(verdict)

        rows.append({
            "type": "TableRow",
            "cells": [
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": endpoint, "size": "Small"}]},
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": f"{p95:.1f} ms", "size": "Small"}]},
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": f"{emoji} {verdict}", "size": "Small"}]},
            ],
        })

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": f"🔍 Per-API Drill-down: {service}", "size": "Large", "weight": "Bolder"},
            {"type": "TextBlock", "text": f"Build: {build_id}", "size": "Small", "isSubtle": True},
            {
                "type": "Table",
                "columns": [{"width": 3}, {"width": 1}, {"width": 1}],
                "firstRowAsHeader": True,
                "rows": [
                    {
                        "type": "TableRow",
                        "cells": [
                            {"type": "TableCell", "items": [{"type": "TextBlock", "text": "Endpoint", "weight": "Bolder", "size": "Small"}]},
                            {"type": "TableCell", "items": [{"type": "TextBlock", "text": "p95 (ms)", "weight": "Bolder", "size": "Small"}]},
                            {"type": "TableCell", "items": [{"type": "TextBlock", "text": "Status", "weight": "Bolder", "size": "Small"}]},
                        ],
                    },
                    *rows,
                ],
            },
        ],
    }

    return {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}


def build_proactive_alert_card(
    service: str,
    build_id: str,
    breach_count: int,
    breaches: list[str],
) -> dict:
    """Build Adaptive Card for proactive alert when a run completes with breaches."""
    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": "⚠️ Performance Run Completed — Action Needed", "size": "Large", "weight": "Bolder", "color": "Attention"},
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Service", "value": service},
                    {"title": "Build", "value": build_id},
                    {"title": "Breaches", "value": str(breach_count)},
                ],
            },
            {"type": "TextBlock", "text": "**Breached Endpoints:**", "spacing": "Medium"},
            {"type": "TextBlock", "text": "\n".join(f"• {b}" for b in breaches), "wrap": True},
        ],
        "actions": [
            {"type": "Action.Submit", "title": "📊 Full Summary", "data": {"action": "quick_status", "service": service, "build_id": build_id}},
        ],
    }

    return {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}


def build_error_card(message: str) -> dict:
    """Build a simple error card."""
    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": "❌ Error", "size": "Medium", "weight": "Bolder", "color": "Attention"},
            {"type": "TextBlock", "text": message, "wrap": True},
        ],
    }
    return {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}


def build_active_runs_card(runs: list[dict]) -> dict:
    """Build card showing currently active test runs."""
    if not runs:
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": [
                {"type": "TextBlock", "text": "✅ No Active Runs", "size": "Medium", "weight": "Bolder"},
                {"type": "TextBlock", "text": "No performance tests are currently running.", "wrap": True},
            ],
        }
    else:
        facts = [{"title": r.get("testName", "unknown"), "value": f"Build: {r.get('buildId', 'N/A')}"} for r in runs]
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": [
                {"type": "TextBlock", "text": "🏃 Active Performance Runs", "size": "Medium", "weight": "Bolder"},
                {"type": "FactSet", "facts": facts},
            ],
        }

    return {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}


def _verdict_emoji(verdict: str) -> str:
    return {"PASS": "✅", "WARN": "⚠️", "BREACH": "❌", "FAIL": "❌"}.get(verdict, "❓")


def _verdict_color(verdict: str) -> str:
    return {"PASS": "Good", "WARN": "Warning", "BREACH": "Attention", "FAIL": "Attention"}.get(verdict, "Default")
