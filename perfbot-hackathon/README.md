# PerfBot — AI-Powered Performance Insights via Microsoft Teams

> **SPARK Global AI Hackathon (June 3–4, 2026)**  
> **Team:** Perf Alchemists  
> **Category:** AI in Engineering  
> **AI Tool:** Azure AI Foundry (GPT-4o)

## Team Members

| Name | Role |
|------|------|
| Sabyasachi Choudhury | Team Lead / Architect |
| Pankaj Dhondiba | Developer |
| Priyanka Deovrat Dongre | Developer |

---

## Problem Statement

After every K6 performance test run, engineers spend **15–30 minutes per service** manually:
- Logging into Grafana and constructing Flux queries against InfluxDB
- Comparing results across builds to detect regressions
- Interpreting metrics using tribal knowledge of thresholds and baselines

This process requires deep familiarity with query syntax, metric names, and historical context — creating a bottleneck where only 2–3 engineers can effectively interpret results.

## Solution

**PerfBot** is a Microsoft Teams bot powered by Azure AI Foundry that answers natural-language questions like:

> *"How did platform-data-api do in the last run?"*

It automatically queries InfluxDB, compares against the previous baseline, detects regressions, and responds with a clear verdict — all within **seconds**.

### What it can do:
- ✅ Check pass/fail status of any service's latest run
- 📊 Show per-API endpoint p95 breakdown
- 🔍 Compare two builds side-by-side
- ⚠️ Detect regressions (>10% degradation in p95)
- 📋 Check SLA compliance (p95 < 2000ms threshold)
- 🔗 Generate Grafana dashboard links with pinned time ranges
- 🔎 Scan all services for failures

---

## Architecture

```
Teams / Web Chat
      │
      ▼
Azure AI Foundry Agent (GPT-4o + system prompt)
      │
      │ calls OpenAPI tool: query_influxdb
      ▼
Azure Function Proxy (Python 3.13, Flex Consumption)
      │
      │ POST /api/v2/query (Token auth)
      ▼
InfluxDB (20.252.97.68:80, org: performance, bucket: k6)
```

### Why an Azure Function proxy?
Foundry agents cannot reach private/internal IPs directly. The Azure Function bridges the gap, also auto-injecting `toFloat()` before aggregation functions (InfluxDB stores values as strings).

---

## Project Structure

```
perfbot-hackathon/
├── README.md                       # This file
├── azure-function/
│   ├── function_app.py             # Azure Function proxy (receives Flux queries, forwards to InfluxDB)
│   ├── requirements.txt            # Python dependencies
│   ├── host.json                   # Azure Functions config
│   └── local.settings.json         # Local dev environment variables
├── foundry-agent/
│   ├── instructions.txt            # Agent system prompt (231 lines)
│   └── openapi-influxdb.json       # OpenAPI spec registered as Foundry tool
├── foundry-sdk/
│   ├── run_agent.py                # SDK sample: invoke PerfBot programmatically
│   ├── requirements.txt            # azure-ai-projects, azure-identity
│   ├── .env.example                # Environment template
│   └── README.md                   # SDK usage instructions
├── docs/
│   ├── architecture.md             # Detailed architecture with Mermaid diagram
│   └── setup-guide.md              # Step-by-step Foundry setup instructions
└── demo/
    └── demo-script.md              # Demo walkthrough script
```

---

## Expected Business Value & ROI

| Metric | Before PerfBot | After PerfBot |
|--------|---------------|---------------|
| Time to get run status | 15–30 min | **5 seconds** |
| Who can interpret results | 2–3 perf engineers | **Anyone on the team** |
| Regression detection | Manual, next-day | **Immediate, proactive** |
| Grafana expertise required | Yes | **No** |

### Quantified ROI
- **~5 engineering hours/week saved** across the performance team (15 min × 20 queries/week)
- **Democratized access**: PMs, QA leads, and developers self-serve without Grafana knowledge
- **Faster feedback loop**: Regressions caught in seconds, not hours — reducing risk of shipping degraded builds
- **Reduced onboarding time**: New team members ask the bot instead of learning Flux query syntax

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Agent | Azure AI Foundry (GPT-4o, version 35) |
| Agent Prompt | Custom instructions (231 lines: Flux templates, SLA rules, service mappings) |
| Tool Bridge | Azure Function (Python 3.13, Flex Consumption plan) |
| Data Source | InfluxDB v2 (HTTP API, Flux queries) |
| Bot Channels | Microsoft Teams, Web Chat, Direct Line |
| Resource Group | rg-hackathon-Perf-Alchemists |

---

## Quick Start (Local Development)

```bash
# 1. Clone this repo
git clone <repo-url>
cd perfbot-hackathon

# 2. Deploy Azure Function
cd azure-function
pip install -r requirements.txt
func start   # or deploy to Azure

# 3. Configure Foundry Agent
# - Create agent in Azure AI Foundry
# - Paste contents of foundry-agent/instructions.txt into agent instructions
# - Add OpenAPI tool using foundry-agent/openapi-influxdb.json
# - Configure connection with Azure Function URL

# 4. Publish to Teams
# - In Foundry: Publish → Teams and Microsoft 365 Copilot
```

See [docs/setup-guide.md](docs/setup-guide.md) for detailed steps.

---

## Demo

See [demo/demo-script.md](demo/demo-script.md) for the 2-minute demo walkthrough.

**Example interaction:**
```
User: "Did platform-data-api pass SLA?"
Bot:  "✅ PASS — all endpoints under SLA threshold.
       p95: 847ms (limit: 2000ms), p90: 612ms (limit: 1500ms).
       Baseline comparison: -3.2% (improvement). No regressions detected."
```
