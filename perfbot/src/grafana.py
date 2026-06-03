"""Grafana URL builder with correct time ranges."""

from src.config import settings


DASHBOARD_UID = "dedlxffenw83kf"
DASHBOARD_SLUG = "k6-performance-test-result-azure"


def build_grafana_url(
    test_name: str,
    test_id: str,
    from_ms: int,
    to_ms: int,
) -> str:
    """Build a Grafana dashboard deep-link with pinned time range.

    IMPORTANT: Always include &from=<epoch_ms>&to=<epoch_ms> to avoid
    defaulting to 'now-6h' which shows no data for historical runs.
    """
    base = settings.grafana_base_url.rstrip("/")
    params = (
        f"?orgId=1"
        f"&from={from_ms}"
        f"&to={to_ms}"
        f"&var-TestId={test_id}"
        f"&var-TestName={test_name}"
        f"&var-Release=NotCaptured"
        f"&var-Namespace=rls-app"
        f"&var-WorkLoadType=deployment"
        f"&var-WorkLoadName={test_name}"
        f"&timezone=browser"
        f"&var-deployment_environment=rls07"
        f"&var-QueueName=-DLQ"
        f"&var-database=c8-perf-rls07"
        f"&var-redis=usw2-c8-redis-perf-rls07-001"
    )
    return f"{base}/d/{DASHBOARD_UID}/{DASHBOARD_SLUG}{params}"
