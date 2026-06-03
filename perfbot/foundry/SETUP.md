# PerfBot — Azure AI Foundry Setup Guide

## Step 1: Paste Instructions

Go to your **PerfBot agent → YAML tab** and replace the empty `instructions: ""` with the full content from `instructions.txt` in this folder.

Or via the Chat tab → click "Instructions" → paste.

---

## Step 2: Add Functions (Tools)

In the Foundry agent UI → **Tools** → **Add** → choose **"Custom function (OpenAPI)"**.

### Option A: Single InfluxDB HTTP tool (simplest)

Since all your queries go to one endpoint (`POST /api/v2/query`), add it as a single HTTP function:

1. **Tools** → **Add** → **OpenAPI** → Upload `openapi-influxdb.json`
2. Configure auth: **API Key** → Header name: `Authorization`, Value: `Token Dqu2kOalfUopQY27lsn9EIuChMbJ1K28agmmyYawwNhh6I19ZBNNt08RSjhkYGjJQ28hSYzPCJCvh86lyDn5HA==`
3. Set server URL: `http://20.252.97.68:80`

The agent will generate Flux queries based on the instructions and send them to InfluxDB.

### Option B: Azure Functions wrapper (recommended for production)

Deploy a lightweight Azure Function that wraps each operation cleanly. The function specs are in `function-definitions.yaml` below.

---

## Step 3: Add Flux Query Templates (Knowledge)

Go to **Knowledge** → **Add** → paste these templates so the agent knows the exact Flux syntax:

### Get Latest Build IDs
```flux
from(bucket: "k6")
  |> range(start: -30d)
  |> filter(fn: (r) => r["testName"] == "{TEST_NAME}")
  |> filter(fn: (r) => r["_measurement"] == "http_req_duration")
  |> filter(fn: (r) => r["_field"] == "value")
  |> keep(columns: ["_time", "testId"])
  |> group(columns: ["testId"])
  |> last(column: "_time")
  |> group()
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {COUNT})
```

### Get Run Summary (Aggregate p95)
```flux
from(bucket: "k6")
  |> range(start: -30d)
  |> filter(fn: (r) => r["testName"] == "{TEST_NAME}")
  |> filter(fn: (r) => r["testId"] == "{BUILD_ID}")
  |> filter(fn: (r) => r["_field"] == "value")
  |> toFloat()
  |> group(columns: ["_measurement", "name"])
  |> quantile(q: 0.95, column: "_value")
```

### Get Per-API Metrics
```flux
from(bucket: "k6")
  |> range(start: -30d)
  |> filter(fn: (r) => r["testName"] == "{TEST_NAME}")
  |> filter(fn: (r) => r["testId"] == "{BUILD_ID}")
  |> filter(fn: (r) => r["_measurement"] == "http_req_duration")
  |> filter(fn: (r) => r["_field"] == "value")
  |> toFloat()
  |> group(columns: ["name"])
  |> quantile(q: 0.95, column: "_value")
```

### Get Time Range (for Grafana links)
```flux
// Min time
from(bucket: "k6")
  |> range(start: -30d)
  |> filter(fn: (r) => r["testName"] == "{TEST_NAME}")
  |> filter(fn: (r) => r["testId"] == "{BUILD_ID}")
  |> filter(fn: (r) => r["_field"] == "value")
  |> keep(columns: ["_time"])
  |> min(column: "_time")

// Max time (same query with max instead of min)
```

### Check Active Runs
```flux
from(bucket: "k6")
  |> range(start: -5m)
  |> filter(fn: (r) => r["_field"] == "value")
  |> keep(columns: ["testName", "testId"])
  |> distinct(column: "testName")
```

---

## Step 4: Publish to Teams

1. Click **Publish** → dropdown → **"Teams and Microsoft 365 Copilot"**
2. Follow the wizard to register the bot and create a Teams app package
3. Once published, anyone in your org can find "PerfBot" in Teams Apps and start chatting

---

## Alternative: Preview Web App (instant sharing)

Click **Publish** → **"Preview web app"** → you get a shareable URL like:
```
https://ai.azure.com/chat/<your-agent-id>
```
Anyone with the link (and org access) can chat with PerfBot immediately.

---

## Notes

- The InfluxDB endpoint (20.252.97.68:80) must be reachable from Azure's network. If it's in your AKS VNet, you may need to expose it or use Azure Functions within the VNet as a proxy.
- The Grafana URL (20.252.97.68:3000) is returned as a link — users need network access to view it.
- For the "Teams and Microsoft 365 Copilot" publish, Foundry handles the Bot Framework registration automatically — no manual App ID/Password needed.
