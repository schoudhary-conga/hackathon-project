"""Comparison logic for performance metrics between runs."""

from src.constants import DEFAULT_THRESHOLDS


def compare_runs(current: dict, baseline: dict) -> dict:
    """Compare current run metrics against baseline.

    Returns comparison dict with deltas and verdicts.
    """
    results = {
        "overall_verdict": "PASS",
        "breaches": [],
        "improvements": [],
        "metrics": [],
    }

    current_endpoints = current.get("endpoints", {})
    baseline_endpoints = baseline.get("endpoints", {})

    all_endpoints = set(current_endpoints.keys()) | set(baseline_endpoints.keys())

    for endpoint in sorted(all_endpoints):
        current_val = current_endpoints.get(endpoint, 0.0)
        baseline_val = baseline_endpoints.get(endpoint, 0.0)

        if baseline_val > 0:
            delta_pct = ((current_val - baseline_val) / baseline_val) * 100
        else:
            delta_pct = 0.0

        threshold = DEFAULT_THRESHOLDS.get("http_req_duration_p95", 2000.0)
        breached = current_val > threshold
        regressed = delta_pct > 10.0  # >10% degradation

        verdict = "PASS"
        if breached:
            verdict = "BREACH"
            results["overall_verdict"] = "FAIL"
            results["breaches"].append(endpoint)
        elif regressed:
            verdict = "WARN"
            if results["overall_verdict"] == "PASS":
                results["overall_verdict"] = "WARN"

        if delta_pct < -10.0:
            results["improvements"].append(endpoint)

        results["metrics"].append({
            "endpoint": endpoint,
            "current_p95": round(current_val, 1),
            "baseline_p95": round(baseline_val, 1),
            "delta_ms": round(current_val - baseline_val, 1),
            "delta_pct": round(delta_pct, 1),
            "verdict": verdict,
        })

    return results


def check_sla(metrics: dict) -> dict:
    """Check if metrics meet SLA thresholds."""
    results = {
        "overall": "PASS",
        "checks": [],
    }

    p95 = metrics.get("p95_overall", 0.0)
    threshold = DEFAULT_THRESHOLDS["http_req_duration_p95"]
    passed = p95 <= threshold
    results["checks"].append({
        "metric": "p95 Response Time",
        "value": round(p95, 1),
        "threshold": threshold,
        "status": "PASS" if passed else "BREACH",
    })
    if not passed:
        results["overall"] = "FAIL"

    return results


def find_regressions(comparison: dict, threshold_pct: float = 10.0) -> list[dict]:
    """Extract only regressed endpoints from comparison."""
    return [
        m for m in comparison.get("metrics", [])
        if m["delta_pct"] > threshold_pct
    ]


def find_slowest_endpoints(metrics: dict, top_n: int = 5) -> list[dict]:
    """Get the N slowest endpoints by p95."""
    endpoints = metrics.get("endpoints", {})
    sorted_eps = sorted(endpoints.items(), key=lambda x: x[1], reverse=True)
    return [
        {"endpoint": name, "p95": round(val, 1)}
        for name, val in sorted_eps[:top_n]
    ]
