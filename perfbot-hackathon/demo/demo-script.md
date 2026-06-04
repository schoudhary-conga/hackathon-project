# PerfBot — Demo Script (2 minutes)

Use this script for the hackathon demo presentation.

---

## Setup Before Demo
- Have Microsoft Teams open with PerfBot chat ready
- Have Foundry Playground open as backup
- Ensure a recent K6 test run exists in InfluxDB (within last 30 days)

---

## Demo Flow

### Scene 1: The Problem (30 seconds)

**Say:** "After every performance test run, our engineers spend 15-30 minutes per service logging into Grafana, writing Flux queries, and manually comparing builds. Only 2-3 people on the team know how to do this. We wanted to make performance insights accessible to everyone — instantly."

### Scene 2: Ask a Simple Question (30 seconds)

**In Teams, type:**
> Did platform-data-api pass SLA in the last run?

**Show the response:** The bot returns a verdict with per-endpoint p95 metrics, flags any SLA breaches (e.g., 304_DocMgt at 54,190ms), and confirms passing endpoints.

**Say:** "Instead of 15 minutes of manual work, we got a full SLA analysis in 5 seconds — and it caught a breach we might have missed."

### Scene 3: Drill Down — Pods & Traces (30 seconds)

**Type:**
> Are the pods healthy for platform-data-api?

**Show the response:** Pod status (Running/CrashLoopBackOff), restart counts, readiness.

**Type:**
> Why is 304_DocMgt slow? Here's the trace: abc123def456

**Show the response:** Trace span breakdown from Grafana Tempo showing where time is spent.

**Say:** "Three tools working together — metrics, pod health, and trace analysis. The bot doesn't just show numbers — it diagnoses root causes like a senior performance engineer."

### Scene 4: Architecture (30 seconds)

**Switch to the architecture slide and say:**

"Under the hood, it's simple:
1. The user asks a question in Teams
2. Azure AI Foundry agent (GPT-4o v35) parses the intent
3. It picks from 3 tools: InfluxDB (metrics), Kubernetes (pods), or Grafana Tempo (traces)
4. An Azure Function proxies the request to the right data source
5. The agent interprets the results and responds in natural language

The total code is one Azure Function with 3 endpoints plus a 349-line system prompt. No custom backend, no database, no web app — just Foundry + one Function."

---

## Backup Questions (if time permits)
- "Any failures today?" → scans all services
- "Compare the last 2 runs for contract-api" → side-by-side
- "What regressed?" → shows only degraded endpoints
- "Show me the Grafana link" → deep link with pinned time range
- "Are pods healthy?" → Kubernetes pod status
- "Why is this API slow? trace: <id>" → Tempo trace breakdown

---

## Key Talking Points
- **5 seconds** vs 15-30 minutes
- **Anyone** can ask, not just perf engineers (PMs, QA, devs)
- **Zero custom backend** — Foundry agent + 1 Azure Function (3 endpoints)
- **3 data sources** — InfluxDB (metrics), Kubernetes (pods), Grafana Tempo (traces)
- **Real data** — querying live systems with actual K6 test results
- **Deployed to Teams** — where engineers already work
- **Catches real breaches** — not just rubber-stamps "pass"
