# PerfBot Demo Chat App

A standalone web-based chat UI that demonstrates PerfBot's performance insights capabilities — no Azure Bot Framework, Teams, InfluxDB, or Azure OpenAI required.

## Quick Start

```bash
cd perfbot
pip install -r demo/requirements.txt
python -m demo.app
```

Then open **http://localhost:8080** in your browser.

## What It Does

This demo app provides the same conversational interface as the Teams bot, but:
- Runs entirely locally as a web app
- Uses **mock data** — no InfluxDB or Azure OpenAI credentials needed
- Renders rich cards with metrics tables, comparison charts, and action buttons
- Demonstrates intent parsing via keyword matching (no LLM dependency)

## Try These Queries

| Query | Intent |
|---|---|
| How did platform-data-api do in the last run? | `quick_status` |
| Which APIs are slowest for scheduler? | `drill_down` |
| Compare the last two runs for contract-api | `comparison` |
| What regressed in dc-ui? | `regressions` |
| Is anything running right now? | `active_runs` |
| Show SLA check for config management | `sla_check` |
| Show Grafana link for contract-api | `grafana_link` |

## Architecture

```
demo/
├── app.py              # FastAPI server + intent routing
├── mock_services.py    # Mock AI brain + InfluxDB (simulated data)
├── requirements.txt    # Python dependencies
└── static/
    └── index.html      # Single-page chat UI (HTML + CSS + JS)
```

The demo reuses the real `src/comparison.py`, `src/charts.py`, `src/grafana.py`, and `src/constants.py` modules from the main perfbot package — only the external service calls (Azure OpenAI + InfluxDB) are mocked.
