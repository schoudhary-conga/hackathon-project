"""InfluxDB client for querying K6 performance metrics."""

import httpx

from src.config import settings
from src.constants import EXCLUDED_METRICS


class InfluxDBClient:
    """Async client for InfluxDB v2 Flux queries."""

    def __init__(self):
        self.url = f"{settings.influxdb_url}/api/v2/query"
        self.org = settings.influxdb_org
        self.token = settings.influxdb_token
        self.bucket = settings.influxdb_bucket

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/vnd.flux",
            "Accept": "application/csv",
        }

    async def query(self, flux: str) -> list[dict]:
        """Execute a Flux query and return parsed rows."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.url,
                params={"org": self.org},
                headers=self._headers,
                content=flux,
            )
            resp.raise_for_status()
            return self._parse_csv(resp.text)

    def _parse_csv(self, csv_text: str) -> list[dict]:
        """Parse InfluxDB CSV response into list of dicts."""
        rows = []
        lines = csv_text.strip().splitlines()
        if len(lines) < 2:
            return rows

        headers = []
        for line in lines:
            line = line.strip()
            if line.startswith("#") or line == "":
                # Reset headers on empty line (new table boundary)
                if line == "":
                    headers = []
                continue
            if not headers:
                headers = line.split(",")
                continue
            values = line.split(",")
            if len(values) == len(headers):
                rows.append(dict(zip(headers, values)))
        return rows

    async def get_latest_build_ids(self, test_name: str, count: int = 2) -> list[str]:
        """Get the N most recent testId values for a service."""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["testName"] == "{test_name}")
  |> filter(fn: (r) => r["_measurement"] == "http_req_duration")
  |> filter(fn: (r) => r["_field"] == "value")
  |> keep(columns: ["_time", "testId"])
  |> group(columns: ["testId"])
  |> last(column: "_time")
  |> group()
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {count})
'''
        rows = await self.query(flux)
        return [r.get("testId", "") for r in rows if r.get("testId")]

    async def get_run_summary(self, test_name: str, build_id: str) -> dict:
        """Get aggregate metrics for a specific run."""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["testName"] == "{test_name}")
  |> filter(fn: (r) => r["testId"] == "{build_id}")
  |> filter(fn: (r) => r["_field"] == "value")
  |> toFloat()
  |> group(columns: ["_measurement", "name"])
  |> quantile(q: 0.95, column: "_value")
'''
        rows = await self.query(flux)
        return self._aggregate_summary(rows)

    async def get_per_api_metrics(self, test_name: str, build_id: str) -> list[dict]:
        """Get per-endpoint p95 metrics for a run."""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["testName"] == "{test_name}")
  |> filter(fn: (r) => r["testId"] == "{build_id}")
  |> filter(fn: (r) => r["_measurement"] == "http_req_duration")
  |> filter(fn: (r) => r["_field"] == "value")
  |> toFloat()
  |> group(columns: ["name"])
  |> quantile(q: 0.95, column: "_value")
'''
        rows = await self.query(flux)
        # Exclude setup calls
        return [
            r for r in rows
            if r.get("name") not in EXCLUDED_METRICS
        ]

    async def get_run_time_range(self, test_name: str, build_id: str) -> tuple[int, int]:
        """Get epoch ms start/end for a run (for Grafana links)."""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["testName"] == "{test_name}")
  |> filter(fn: (r) => r["testId"] == "{build_id}")
  |> filter(fn: (r) => r["_field"] == "value")
  |> keep(columns: ["_time"])
  |> min(column: "_time")
'''
        start_rows = await self.query(flux)

        flux_end = flux.replace("min(", "max(")
        end_rows = await self.query(flux_end)

        start_ms = self._time_to_epoch_ms(start_rows[0]["_time"]) if start_rows else 0
        end_ms = self._time_to_epoch_ms(end_rows[0]["_time"]) if end_rows else 0
        return start_ms, end_ms

    async def check_active_runs(self) -> list[dict]:
        """Check for currently active test runs (data in last 5 min)."""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -5m)
  |> filter(fn: (r) => r["_field"] == "value")
  |> keep(columns: ["testName", "testId"])
  |> distinct(column: "testName")
'''
        return await self.query(flux)

    async def get_test_details(self, test_name: str, test_id: str | None = None) -> dict | None:
        """Get test execution details from testDetails counter or http_req_duration tags."""
        # First try the testDetails counter measurement
        id_filter = f'  |> filter(fn: (r) => r["testId"] == "{test_id}")\n' if test_id else ""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["_measurement"] == "testDetails")
  |> filter(fn: (r) => r["testName"] == "{test_name}")
{id_filter}  |> last()
'''
        rows = await self.query(flux)
        if rows:
            detail = {}
            for row in rows:
                detail.update(row)
            for key in ("", "result", "table", "_start", "_stop", "_field", "_measurement", "_value"):
                detail.pop(key, None)
            return detail

        # Fallback: extract metadata from http_req_duration tags
        flux_fallback = f'''
from(bucket: "{self.bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["_measurement"] == "http_req_duration")
  |> filter(fn: (r) => r["testName"] == "{test_name}")
{id_filter}  |> filter(fn: (r) => r["_field"] == "value")
  |> group()
  |> limit(n: 1)
'''
        rows = await self.query(flux_fallback)
        if not rows:
            return None

        row = rows[0]
        # Get time range and instance count for VU estimation
        time_flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["_measurement"] == "http_req_duration")
  |> filter(fn: (r) => r["testName"] == "{test_name}")
{id_filter}  |> filter(fn: (r) => r["_field"] == "value")
  |> keep(columns: ["_time", "instance_id"])
  |> group()
  |> reduce(fn: (r, accumulator) => ({{
      min_time: if r._time < accumulator.min_time then r._time else accumulator.min_time,
      max_time: if r._time > accumulator.max_time then r._time else accumulator.max_time,
    }}),
    identity: {{min_time: 2099-01-01T00:00:00Z, max_time: 1970-01-01T00:00:00Z}})
'''
        detail = {
            "testName": row.get("testName", test_name),
            "testId": row.get("testId", test_id or ""),
            "scenario": row.get("scenario", ""),
            "job_name": row.get("job_name", ""),
            "method": row.get("method", ""),
            "source": "inferred from http_req_duration tags",
        }
        # Clean empty values
        return {k: v for k, v in detail.items() if v}

    def _aggregate_summary(self, rows: list[dict]) -> dict:
        """Aggregate raw rows into a summary dict."""
        summary = {
            "p95_overall": 0.0,
            "total_requests": 0,
            "error_rate": 0.0,
            "endpoints": {},
        }
        for row in rows:
            name = row.get("name", "unknown")
            value = float(row.get("_value", 0))
            measurement = row.get("_measurement", "")

            if name not in EXCLUDED_METRICS:
                if measurement == "http_req_duration":
                    summary["endpoints"][name] = value
                    summary["p95_overall"] = max(summary["p95_overall"], value)

        return summary

    def _time_to_epoch_ms(self, time_str: str) -> int:
        """Convert InfluxDB time string to epoch milliseconds."""
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except (ValueError, AttributeError):
            return 0


influxdb_client = InfluxDBClient()
