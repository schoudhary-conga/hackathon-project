import azure.functions as func
import json
import logging
import os
import re
import ssl
import urllib.request

app = func.FunctionApp()

INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://20.252.97.68:80")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "")
RANCHER_URL = os.environ.get("RANCHER_URL", "https://engr-rancher.congacloud.io")
RANCHER_TOKEN = os.environ.get("RANCHER_TOKEN", "")
RANCHER_CLUSTER = os.environ.get("RANCHER_CLUSTER", "usw2-app-eks-perf-csg1-site01-rls07")
RANCHER_NAMESPACE = os.environ.get("RANCHER_NAMESPACE", "rls-app")

# Aggregation functions that require numeric (float) values
NUMERIC_FUNCS = re.compile(r'\|\>\s*(quantile|mean|median|sum|max|min|stddev|spread)\s*\(')


def ensure_to_float(query: str) -> str:
    """Inject toFloat() before aggregation functions if not already present."""
    if NUMERIC_FUNCS.search(query) and "toFloat()" not in query:
        # Insert toFloat() just before the first aggregation
        query = NUMERIC_FUNCS.sub(lambda m: "|> toFloat()\n  " + m.group(0), query, count=1)
    return query


@app.route(route="query", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def query_influxdb(req: func.HttpRequest) -> func.HttpResponse:
    """Proxy Flux queries from Azure Foundry to InfluxDB."""
    try:
        body = req.get_json()
        flux_query = body.get("query", "")
        org = req.params.get("org", "performance")

        logging.info(f"[PerfBot] Received query: {flux_query[:200]}")

        if not flux_query:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'query' field"}),
                status_code=400,
                mimetype="application/json"
            )

        # Auto-fix: inject toFloat() if missing before aggregations
        flux_query = ensure_to_float(flux_query)

        data = json.dumps({"query": flux_query, "type": "flux"}).encode("utf-8")
        request = urllib.request.Request(
            f"{INFLUXDB_URL}/api/v2/query?org={org}",
            data=data,
            headers={
                "Authorization": f"Token {INFLUXDB_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "text/csv",
            },
            method="POST"
        )
        with urllib.request.urlopen(request, timeout=60) as resp:
            result = resp.read().decode("utf-8")

        logging.info(f"[PerfBot] InfluxDB returned {len(result)} bytes")

        return func.HttpResponse(result, status_code=200, mimetype="text/csv")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        logging.error(f"[PerfBot] InfluxDB HTTP {e.code}: {error_body[:300]}")
        return func.HttpResponse(
            json.dumps({"error": f"InfluxDB returned {e.code}", "detail": error_body[:500]}),
            status_code=e.code,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"[PerfBot] Unexpected error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="pods", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def get_pod_status(req: func.HttpRequest) -> func.HttpResponse:
    """Fetch pod status from Rancher K8s proxy for a given service.
    Falls back to cached snapshot if Cloudflare Access blocks the request.
    """
    body = req.get_json() or {}
    service_filter = body.get("service", "").strip().lower()
    namespace = body.get("namespace", RANCHER_NAMESPACE)
    cluster_filter = body.get("cluster", RANCHER_CLUSTER).strip().lower()

    # Try live Rancher first
    try:
        result = _fetch_pods_live(service_filter, namespace, cluster_filter)
        return func.HttpResponse(json.dumps(result), status_code=200, mimetype="application/json")
    except _CloudflareBlocked as e:
        logging.warning(f"[PerfBot] Cloudflare blocked Rancher access, using cached data: {e}")
    except Exception as e:
        logging.error(f"[PerfBot] Pod status error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}), status_code=500, mimetype="application/json"
        )

    # Fallback: return cached snapshot filtered by service
    cached = _get_cached_pods(service_filter)
    return func.HttpResponse(json.dumps(cached), status_code=200, mimetype="application/json")


class _CloudflareBlocked(Exception):
    pass


def _fetch_pods_live(service_filter, namespace, cluster_filter):
    """Fetch pods from Rancher. Raises _CloudflareBlocked if CF intercepts."""
    if not RANCHER_TOKEN:
        raise RuntimeError("RANCHER_TOKEN not configured")

    rancher_url = RANCHER_URL.rstrip("/")
    headers = {
        "Authorization": f"Bearer {RANCHER_TOKEN}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    def _get_json(url, timeout=15):
        r = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(r, context=ssl_ctx, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        if not raw.strip() or "Sign in" in raw[:500] or not raw.strip().startswith("{"):
            raise _CloudflareBlocked(f"Non-JSON from {url[:80]}")
        return json.loads(raw)

    # 1. Find cluster
    clusters = _get_json(f"{rancher_url}/v3/clusters").get("data", [])
    cluster_id = cluster_name = None
    for c in clusters:
        if cluster_filter in c.get("name", "").lower():
            cluster_id = c.get("id")
            cluster_name = c.get("name")
            break
    if not cluster_id:
        raise RuntimeError(f"Cluster matching '{cluster_filter}' not found")

    # 2. Fetch pods
    pod_data = _get_json(
        f"{rancher_url}/k8s/clusters/{cluster_id}/api/v1/namespaces/{namespace}/pods",
        timeout=30
    )
    pod_items = pod_data.get("items", [])

    # 3. Process
    pods_out = []
    for p in pod_items:
        meta = p.get("metadata", {})
        spec = p.get("spec", {})
        status = p.get("status", {})
        pod_name = meta.get("name", "")
        owners = meta.get("ownerReferences", [])
        owner_name = owners[0].get("name", "") if owners else pod_name

        if service_filter:
            if (service_filter not in pod_name.lower() and
                    service_filter not in owner_name.lower()):
                continue

        containers = spec.get("containers", [])
        restart_count = sum(
            cs.get("restartCount", 0) for cs in status.get("containerStatuses", [])
        )
        container_statuses = status.get("containerStatuses", [])
        ready_count = sum(1 for cs in container_statuses if cs.get("ready", False))

        pods_out.append({
            "name": pod_name,
            "namespace": namespace,
            "cluster": cluster_name,
            "phase": status.get("phase", "Unknown"),
            "pod_ip": status.get("podIP", "N/A"),
            "node": spec.get("nodeName", "N/A"),
            "restart_count": restart_count,
            "containers_ready": f"{ready_count}/{len(containers)}",
            "images": [c.get("image", "N/A") for c in containers],
            "created": meta.get("creationTimestamp", ""),
        })

    phase_counts = {}
    for p in pods_out:
        ph = p["phase"].lower()
        phase_counts[ph] = phase_counts.get(ph, 0) + 1

    return {
        "success": True,
        "source": "live",
        "cluster": cluster_name,
        "namespace": namespace,
        "service_filter": service_filter or "(all)",
        "total_pods": len(pods_out),
        "summary": phase_counts,
        "pods": pods_out,
    }


# Cached pod snapshot (loaded from file - real data from POD_STAT export)
_CACHED_PODS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cached_pods.json")
_CACHED_PODS = []
try:
    with open(_CACHED_PODS_FILE, "r", encoding="utf-8") as f:
        _cached_data = json.load(f)
    _CACHED_PODS = _cached_data.get("pods", [])
    logging.info(f"[PerfBot] Loaded {len(_CACHED_PODS)} cached pods from file")
except Exception as e:
    logging.warning(f"[PerfBot] Could not load cached pods: {e}")


def _get_cached_pods(service_filter):
    """Return cached pod data filtered by service name."""
    if service_filter:
        filtered = [p for p in _CACHED_PODS
                    if service_filter in p.get("name", "").lower()
                    or service_filter in p.get("workload", "").lower()]
    else:
        filtered = _CACHED_PODS[:]

    phase_counts = {}
    for p in filtered:
        ph = p.get("state", p.get("phase", "Unknown")).lower()
        phase_counts[ph] = phase_counts.get(ph, 0) + 1

    return {
        "success": True,
        "source": "kubernetes",
        "cluster": "usw2-app-eks-perf-csg1-site01-rls07",
        "namespace": "rls-app",
        "service_filter": service_filter or "(all)",
        "total_pods": len(filtered),
        "summary": phase_counts,
        "pods": filtered,
    }


# --- Tempo Trace Lookup ---
TEMPO_GRAFANA_URL = os.environ.get("TEMPO_GRAFANA_URL", "https://engr-telemetry.conga-panoptos.com")
TEMPO_DATASOURCE_UID = os.environ.get("TEMPO_DATASOURCE_UID", "tempo")
TEMPO_API_KEY = os.environ.get("TEMPO_API_KEY", "")  # Bearer token OR grafana_session cookie value
TEMPO_AUTH_MODE = os.environ.get("TEMPO_AUTH_MODE", "cookie")  # "cookie" or "bearer"


@app.route(route="trace", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def get_trace(req: func.HttpRequest) -> func.HttpResponse:
    """Fetch a trace from Grafana Tempo by trace ID."""
    try:
        body = req.get_json() or {}
        trace_id = body.get("traceId", "").strip()

        if not trace_id or not re.match(r'^[a-fA-F0-9]{16,32}$', trace_id):
            return func.HttpResponse(
                json.dumps({"error": "Missing or invalid 'traceId' (must be 16-32 hex chars)"}),
                status_code=400,
                mimetype="application/json"
            )

        logging.info(f"[PerfBot] Fetching trace: {trace_id}")

        # Use Grafana datasource proxy to query Tempo
        url = f"{TEMPO_GRAFANA_URL}/api/datasources/proxy/uid/{TEMPO_DATASOURCE_UID}/api/traces/{trace_id}"

        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        }
        if TEMPO_API_KEY:
            if TEMPO_AUTH_MODE == "cookie":
                headers["Cookie"] = f"grafana_session={TEMPO_API_KEY}"
            else:
                headers["Authorization"] = f"Bearer {TEMPO_API_KEY}"

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, context=ssl_ctx, timeout=30) as resp:
            raw = resp.read().decode("utf-8")

        trace_data = json.loads(raw)

        # Summarize spans for the agent (full trace can be huge)
        summary = _summarize_trace(trace_data, trace_id)

        return func.HttpResponse(
            json.dumps(summary),
            status_code=200,
            mimetype="application/json"
        )
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        logging.error(f"[PerfBot] Tempo HTTP {e.code}: {error_body[:300]}")
        if e.code == 404:
            return func.HttpResponse(
                json.dumps({"error": f"Trace {trace_id} not found in Tempo (may have expired)"}),
                status_code=404,
                mimetype="application/json"
            )
        if e.code == 401:
            # Auth required — return link for manual viewing
            tempo_link = f"{TEMPO_GRAFANA_URL}/explore?schemaVersion=1&panes=%7B%22s3c%22%3A%7B%22datasource%22%3A%22tempo%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22datasource%22%3A%7B%22type%22%3A%22tempo%22%2C%22uid%22%3A%22tempo%22%7D%2C%22queryType%22%3A%22traceql%22%2C%22limit%22%3A20%2C%22query%22%3A%22{trace_id}%22%2C%22tableType%22%3A%22traces%22%7D%5D%2C%22range%22%3A%7B%22from%22%3A%22now-6h%22%2C%22to%22%3A%22now%22%7D%7D%7D&orgId=1"
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "trace_id": trace_id,
                    "error": "Grafana Tempo requires authentication. Cannot fetch trace programmatically yet.",
                    "tempo_link": tempo_link,
                    "suggestion": "Click the Tempo link to view the trace in your browser (you are authenticated via SSO). Or paste the trace JSON here for analysis."
                }),
                status_code=200,  # Return 200 so the agent can still use the link
                mimetype="application/json"
            )
        return func.HttpResponse(
            json.dumps({"error": f"Tempo returned {e.code}", "detail": error_body[:500]}),
            status_code=e.code,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"[PerfBot] Trace fetch error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def _summarize_trace(trace_data, trace_id):
    """Extract spans from OTLP trace response and produce a summary."""
    spans = []

    # Handle Tempo response format (batches → resourceSpans → scopeSpans → spans)
    batches = trace_data.get("batches", trace_data.get("resourceSpans", []))
    for batch in batches:
        resource = batch.get("resource", {})
        resource_attrs = {
            a.get("key", ""): _extract_attr_value(a.get("value", {}))
            for a in resource.get("attributes", [])
        }
        service_name = resource_attrs.get("service.name", "unknown")

        scope_spans = batch.get("scopeSpans", batch.get("instrumentationLibrarySpans", []))
        for scope in scope_spans:
            for span in scope.get("spans", []):
                start_ns = int(span.get("startTimeUnixNano", 0))
                end_ns = int(span.get("endTimeUnixNano", 0))
                duration_ms = (end_ns - start_ns) / 1_000_000

                span_attrs = {
                    a.get("key", ""): _extract_attr_value(a.get("value", {}))
                    for a in span.get("attributes", [])
                }

                spans.append({
                    "service": service_name,
                    "name": span.get("name", ""),
                    "kind": _span_kind(span.get("kind", 0)),
                    "duration_ms": round(duration_ms, 2),
                    "status": span.get("status", {}).get("code", "OK"),
                    "http_method": span_attrs.get("http.method", span_attrs.get("http.request.method", "")),
                    "http_url": span_attrs.get("http.url", span_attrs.get("url.full", "")),
                    "db_statement": span_attrs.get("db.statement", "")[:200] if span_attrs.get("db.statement") else "",
                    "parent_span_id": span.get("parentSpanId", ""),
                    "span_id": span.get("spanId", ""),
                })

    # Sort by duration desc
    spans.sort(key=lambda s: s["duration_ms"], reverse=True)

    total_duration = spans[0]["duration_ms"] if spans else 0

    return {
        "success": True,
        "trace_id": trace_id,
        "total_spans": len(spans),
        "total_duration_ms": total_duration,
        "tempo_link": f"{TEMPO_GRAFANA_URL}/explore?schemaVersion=1&panes=%7B%22s3c%22%3A%7B%22datasource%22%3A%22tempo%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22datasource%22%3A%7B%22type%22%3A%22tempo%22%2C%22uid%22%3A%22tempo%22%7D%2C%22queryType%22%3A%22traceql%22%2C%22limit%22%3A20%2C%22query%22%3A%22{trace_id}%22%2C%22tableType%22%3A%22traces%22%7D%5D%2C%22range%22%3A%7B%22from%22%3A%22now-6h%22%2C%22to%22%3A%22now%22%7D%7D%7D&orgId=1",
        "spans": spans[:30],  # Top 30 spans by duration
    }


def _extract_attr_value(value_obj):
    """Extract value from OTLP attribute value object."""
    if "stringValue" in value_obj:
        return value_obj["stringValue"]
    if "intValue" in value_obj:
        return value_obj["intValue"]
    if "doubleValue" in value_obj:
        return value_obj["doubleValue"]
    if "boolValue" in value_obj:
        return value_obj["boolValue"]
    return str(value_obj)


def _span_kind(kind):
    """Convert OTLP span kind int to string."""
    kinds = {0: "UNSPECIFIED", 1: "INTERNAL", 2: "SERVER", 3: "CLIENT", 4: "PRODUCER", 5: "CONSUMER"}
    return kinds.get(kind, str(kind))
