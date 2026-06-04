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
> How did platform-objectdb-api do in the last run?

**Show the response:** The bot returns a clear verdict (PASS/FAIL), p95 metrics per endpoint, comparison against baseline, and a Grafana link.

**Say:** "Instead of 15 minutes of manual work, we got a full analysis in 5 seconds."

### Scene 3: Drill Down (30 seconds)

**Type:**
> Which APIs are slowest?

**Show the response:** Per-API p95 ranking with the slowest endpoints highlighted.

**Type:**
> Is it safe to deploy?

**Show the response:** The bot gives an expert-level recommendation with reasoning.

**Say:** "The bot doesn't just show numbers — it thinks like a senior performance engineer. It tells you what regressed, why it might have happened, and what to do next."

### Scene 4: Architecture (30 seconds)

**Switch to the architecture slide and say:**

"Under the hood, it's simple:
1. The user asks a question in Teams
2. Azure AI Foundry agent (GPT-4o) parses the intent and generates a Flux query
3. An Azure Function proxies the query to our InfluxDB
4. The agent interprets the CSV results and responds in natural language

The total code is just one Azure Function (75 lines of Python) plus a 231-line system prompt. No custom backend, no database, no web app — just Foundry + one Function."

---

## Backup Questions (if time permits)
- "Any failures today?" → scans all services
- "Compare the last 2 runs for contract-api" → side-by-side
- "What regressed?" → shows only degraded endpoints
- "Show me the Grafana link" → deep link with pinned time range

---

## Key Talking Points
- **5 seconds** vs 15-30 minutes
- **Anyone** can ask, not just perf engineers (PMs, QA, devs)
- **Zero custom backend** — Foundry agent + 1 Azure Function
- **Real data** — querying live InfluxDB with actual K6 test results
- **Deployed to Teams** — where engineers already work
