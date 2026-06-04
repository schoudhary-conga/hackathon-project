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
- ⚙️ Check pod health (phase, restarts, readiness) via Kubernetes
- 🧬 Root cause analysis via Grafana Tempo trace spans

---

## Architecture

```
Teams / Web Chat
      │
      ▼
Azure AI Foundry Agent (GPT-4o v35 + 349-line system prompt)
      │
      │ calls 3 OpenAPI tools
      ▼
Azure Function Proxy (Python 3.13, Flex Consumption)
      │
      ├── POST /api/query   → InfluxDB (K6 metrics)
      ├── GET  /api/pods    → Kubernetes (pod health)
      └── GET  /api/trace   → Grafana Tempo (trace spans)
      │
      ▼
┌─────────────────────────────────────────────┐
│  InfluxDB        │ Kubernetes  │ Grafana    │
│  (metrics/SLA)   │ (pods)      │ Tempo(RCA) │
└─────────────────────────────────────────────┘
```

### Why an Azure Function proxy?
Foundry agents cannot reach private/internal IPs directly. The Azure Function bridges the gap, also:
- Auto-injecting `toFloat()` before aggregation functions (InfluxDB stores values as strings)
- Providing Cloudflare fallback with cached pod snapshots when Rancher is unreachable
- Validating trace IDs (hex, 16–32 chars) before forwarding to Tempo

---

## Project Structure

```
perfbot-hackathon/
├── README.md                       # This file
├── .gitignore                      # Git ignore rules
├── azure-function/
│   ├── function_app.py             # Azure Function proxy (3 endpoints: query, pods, trace)
│   ├── cached_pods.json            # Fallback pod snapshot (Cloudflare bypass)
│   ├── requirements.txt            # Python dependencies
│   ├── host.json                   # Azure Functions config
│   └── local.settings.json         # Local dev environment variables
├── foundry-agent/
│   ├── instructions.txt            # Agent system prompt (349 lines)
│   ├── openapi-influxdb.json       # OpenAPI spec: InfluxDB query tool
│   ├── openapi-pods.json           # OpenAPI spec: Kubernetes pods tool
│   └── openapi-trace.json          # OpenAPI spec: Grafana Tempo trace tool
├── foundry-sdk/
│   ├── run_agent.py                # SDK sample: invoke PerfBot programmatically
│   ├── install.sh                  # One-command setup script
│   ├── INSTRUCTIONS.md             # Detailed SDK usage guide
│   ├── requirements.txt            # azure-ai-projects, azure-identity
│   ├── .env.example                # Environment template
│   └── README.md                   # SDK usage instructions
├── docs/
│   ├── architecture.md             # Detailed architecture with Mermaid diagram
│   └── setup-guide.md              # Step-by-step Foundry setup instructions
└── demo/
    ├── PerfBot-Hackathon-Deck.pptx # Presentation deck
    ├── demo-script.md              # Demo walkthrough script
    └── powerpoint-outline.md       # Slide outline reference
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
| Agent Prompt | Custom instructions (349 lines: Flux templates, SLA rules, service mappings) |
| Tool Bridge | Azure Function (Python 3.13, Flex Consumption plan) — 3 endpoints |
| Data Sources | InfluxDB v2 (metrics), Kubernetes (pods), Grafana Tempo (traces) |
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
# - Add 3 OpenAPI tools: openapi-influxdb.json, openapi-pods.json, openapi-trace.json
# - Configure connection with Azure Function URL

# 4. Publish to Teams
# - In Foundry: Publish → Teams and Microsoft 365 Copilot
```

See [docs/setup-guide.md](docs/setup-guide.md) for detailed setup steps.

---

## Demo

See [demo/demo-script.md](demo/demo-script.md) for the 2-minute demo walkthrough.

**Example interaction:**
```
User: "Did platform-data-api pass SLA in the last run?"
Bot:  "⚠️ BREACH — 5/6 endpoints PASS (p95 < 2000ms).
       304_DocMgt_RetrievesMultipleDoc: p95 = 54,190ms → SLA BREACH
       Create/Read/Update/Delete: all < 310ms → PASS"
```
