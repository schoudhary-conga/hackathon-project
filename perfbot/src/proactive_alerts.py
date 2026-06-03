"""Proactive alerts — polls for completed runs and pushes to Teams channel."""

import asyncio
import httpx

from src.config import settings
from src.influxdb_client import influxdb_client
from src.comparison import check_sla
from src.cards import build_proactive_alert_card
from src.constants import SERVICE_MAPPINGS


# Track last seen buildId per service to detect new completions
_last_seen: dict[str, str] = {}


async def check_for_completed_runs():
    """Poll InfluxDB for newly completed runs and send alerts if breaches found."""
    all_test_names = set(SERVICE_MAPPINGS.values())

    for test_name in all_test_names:
        try:
            build_ids = await influxdb_client.get_latest_build_ids(test_name, count=1)
            if not build_ids:
                continue

            latest_id = build_ids[0]
            if _last_seen.get(test_name) == latest_id:
                continue  # Already processed

            _last_seen[test_name] = latest_id

            # Check if this run has breaches
            metrics = await influxdb_client.get_run_summary(test_name, latest_id)
            sla = check_sla(metrics)

            if sla["overall"] == "FAIL":
                breaches = [c["metric"] for c in sla["checks"] if c["status"] == "BREACH"]
                card = build_proactive_alert_card(test_name, latest_id, len(breaches), breaches)
                await _send_to_teams_channel(card)

        except Exception as e:
            print(f"[ALERT] Error checking {test_name}: {e}")


async def _send_to_teams_channel(card: dict):
    """Send an Adaptive Card to the configured Teams webhook."""
    if not settings.teams_webhook_url:
        print("[ALERT] No Teams webhook URL configured, skipping alert.")
        return

    payload = {
        "type": "message",
        "attachments": [card],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(settings.teams_webhook_url, json=payload)
        if resp.status_code == 200:
            print("[ALERT] Successfully sent proactive alert to Teams.")
        else:
            print(f"[ALERT] Failed to send alert: {resp.status_code} {resp.text}")


async def run_alert_loop(interval_seconds: int = 300):
    """Run the proactive alert polling loop (every 5 min by default)."""
    print(f"[ALERT] Starting proactive alert loop (every {interval_seconds}s)")
    while True:
        await check_for_completed_runs()
        await asyncio.sleep(interval_seconds)
