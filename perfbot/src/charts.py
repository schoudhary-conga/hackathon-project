"""Chart generation for performance metrics using matplotlib."""

import io
import base64

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt


def generate_comparison_chart(comparison: dict) -> str:
    """Generate a bar chart comparing current vs baseline p95 values.

    Returns base64-encoded PNG image.
    """
    metrics = comparison.get("metrics", [])
    if not metrics:
        return ""

    # Limit to top 10 endpoints for readability
    metrics = sorted(metrics, key=lambda m: m["current_p95"], reverse=True)[:10]

    endpoints = [m["endpoint"] for m in metrics]
    current_vals = [m["current_p95"] for m in metrics]
    baseline_vals = [m["baseline_p95"] for m in metrics]

    # Shorten endpoint names for display
    short_names = [_shorten_name(e) for e in endpoints]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = range(len(short_names))
    width = 0.35

    bars1 = ax.bar([i - width / 2 for i in x], baseline_vals, width, label="Baseline", color="#4A90D9", alpha=0.8)
    bars2 = ax.bar([i + width / 2 for i in x], current_vals, width, label="Current", color="#E85D75", alpha=0.8)

    ax.set_xlabel("Endpoint")
    ax.set_ylabel("p95 Response Time (ms)")
    ax.set_title("Performance Comparison: Current vs Baseline")
    ax.set_xticks(list(x))
    ax.set_xticklabels(short_names, rotation=45, ha="right", fontsize=8)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode("utf-8")


def generate_trend_chart(trend_data: list[dict], service_name: str) -> str:
    """Generate a line chart showing p95 trends over multiple runs.

    trend_data: list of {"build_id": str, "p95": float}
    Returns base64-encoded PNG image.
    """
    if not trend_data:
        return ""

    build_ids = [d["build_id"][-8:] for d in trend_data]  # Shorten IDs
    p95_values = [d["p95"] for d in trend_data]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(build_ids, p95_values, marker="o", linewidth=2, color="#4A90D9")
    ax.fill_between(build_ids, p95_values, alpha=0.1, color="#4A90D9")

    ax.set_xlabel("Build ID")
    ax.set_ylabel("p95 Response Time (ms)")
    ax.set_title(f"Performance Trend: {service_name}")
    ax.grid(alpha=0.3)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode("utf-8")


def _shorten_name(name: str, max_len: int = 20) -> str:
    """Shorten endpoint name for chart labels."""
    if len(name) <= max_len:
        return name
    return name[:max_len - 3] + "..."
