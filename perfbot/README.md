# PerfBot — AI-Powered Performance Insights via Microsoft Teams

> **SPARK Global AI Hackathon (June 3-4, 2026)**
> Team: Perf Alchemists | Category: AI in Engineering | AI Tool: Azure AI Foundry

## What It Does

PerfBot is a Teams bot that answers natural-language questions about K6 performance test results. Instead of manually querying Grafana/InfluxDB (15-30 min), engineers type a question and get an Adaptive Card with metrics, charts, and insights in seconds.

**Example:**
> "How did platform-data-api do in the last run?"

→ Adaptive Card with comparison table, bar chart, pass/fail verdict, and Grafana link.

---

## Project Structure

```
perfbot/
├── app.py                      # Entry point (aiohttp server)
├── Dockerfile                  # Container image
├── pyproject.toml              # Dependencies
├── requirements.txt            # Pip requirements
├── .env.example                # Environment variable template
├── src/
│   ├── config.py               # Settings from env vars
│   ├── constants.py            # Service mappings, thresholds
│   ├── ai_brain.py             # Azure OpenAI intent parsing
│   ├── influxdb_client.py      # InfluxDB Flux query client
│   ├── comparison.py           # Metrics comparison logic
│   ├── charts.py               # matplotlib chart generation
│   ├── cards.py                # Adaptive Card builders
│   ├── grafana.py              # Grafana URL builder
│   ├── handlers.py             # Intent routing & orchestration
│   ├── bot.py                  # Teams Bot activity handler
│   └── proactive_alerts.py     # Polling loop for breach alerts
├── deploy/
│   ├── deployment.yaml         # K8s deployment manifest
│   └── secrets.yaml            # Secret template (fill values)
└── teams-manifest/
    └── manifest.json           # Teams app manifest
```

---

## Setup Steps

### Prerequisites

- Python 3.12+
- Azure subscription with:
  - Azure Bot registration (Bot Framework)
  - Azure OpenAI resource with GPT-4o deployment
- Access to InfluxDB at `http://20.252.97.68:80` (org: `performance`)
- Docker (for containerized deployment)

### 1. Clone & Install

```bash
cd perfbot
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual values:
#   - MICROSOFT_APP_ID / PASSWORD from Azure Bot registration
#   - AZURE_OPENAI_ENDPOINT / API_KEY from Azure OpenAI resource
#   - INFLUXDB_TOKEN from kubectl secret
```

### 3. Run Locally

```bash
python app.py
# Server starts on http://localhost:3978
```

Use [Bot Framework Emulator](https://github.com/microsoft/BotFramework-Emulator) to test locally, or use [ngrok](https://ngrok.com/) to expose locally for Teams:

```bash
ngrok http 3978
# Set messaging endpoint in Azure Bot: https://<ngrok-url>/api/messages
```

### 4. Register Azure Bot

1. Go to Azure Portal → Create "Azure Bot" resource
2. Set **Messaging endpoint** to `https://<your-host>/api/messages`
3. Under **Channels**, add Microsoft Teams
4. Copy App ID and Password to your `.env`

### 5. Deploy to Teams

**Option A: Azure App Service**
```bash
az acr build --registry congaperformance --image perfbot:v0.1.0 .
az webapp create --resource-group perf-rg --plan perf-plan --name perfbot \
  --deployment-container-image-name congaperformance.azurecr.io/perfbot:v0.1.0
```

**Option B: AKS (existing cluster)**
```bash
docker build -t congaperformance.azurecr.io/perfbot:v0.1.0 .
docker push congaperformance.azurecr.io/perfbot:v0.1.0
# Update deploy/secrets.yaml with real values
kubectl apply -f deploy/secrets.yaml
kubectl apply -f deploy/deployment.yaml
```

### 6. Install Teams App

1. Zip contents of `teams-manifest/` (manifest.json + icon files)
2. In Teams Admin → Manage apps → Upload custom app
3. Or sideload for testing: Teams → Apps → Upload a custom app

---

## Supported Queries

| Query | What it does |
|-------|-------------|
| "How did platform-data-api do?" | Latest run summary vs baseline |
| "Did last night's run pass?" | Pass/Fail verdict |
| "Any failures today?" | Scan all services for breaches |
| "Compare build X vs Y" | Side-by-side comparison |
| "Which APIs are slowest?" | Per-endpoint p95 ranking |
| "What regressed?" | Only endpoints with >10% degradation |
| "Is platform-data-api within SLA?" | Threshold check |
| "Is anything running right now?" | Active TestRuns |
| "Show Grafana link" | Deep-link with correct time range |

**Fuzzy resolution works:** "platform data", "PDA", "scheduler", "dc ui" all resolve to the correct testName.

---

## Architecture

```
User (Teams) → Bot Framework → Azure OpenAI (intent + resolution)
                                        ↓
                               InfluxDB HTTP API (Flux queries)
                                        ↓
                               Comparison Logic (deltas, SLA check)
                                        ↓
                               Chart Gen (matplotlib → base64 PNG)
                                        ↓
                               Adaptive Card (table + chart + insight)
                                        ↓
                               Teams Response ← Bot Framework
```

---

## Key Design Decisions

- **InfluxDB org**: `performance` (NEVER `conga`)
- **toFloat()**: Always applied before aggregation (values stored as strings)
- **Excluded metrics**: `getBuildId`, `generateClientCredentialsToken` (setup calls)
- **Grafana links**: Always include `&from=<epoch_ms>&to=<epoch_ms>`
- **LLM temperature**: 0.0 for intent parsing (deterministic), 0.3 for insights (creative)

---

## Demo Script (2 min)

1. Open Teams → type: *"How did platform-data-api do in the last run?"*
2. Bot responds with Adaptive Card (table + chart + insight + Grafana button)
3. Click **"Show Per-API"** → drill-down card with per-endpoint breakdown
4. Show proactive alert that was pushed automatically when a run breached
5. Type: *"anything concerning?"* → bot scans all services, highlights breaches
