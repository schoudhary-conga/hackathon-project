# PerfBot — AI-Powered Performance Insights via Microsoft Teams

> **SPARK Global AI Hackathon | June 3–4, 2026**  
> **Team:** Perf Alchemists  
> **Category:** AI in Engineering  
> **AI Tool:** Azure AI Foundry (GPT-4o v35)

## What is PerfBot?

PerfBot is a Microsoft Teams bot that answers natural-language questions about K6 performance test results. Instead of spending 15–30 minutes manually querying Grafana/InfluxDB, engineers simply ask:

> *"Did platform-data-api pass SLA in the last run?"*

And get an instant, expert-level answer — with SLA verdicts, per-API breakdowns, pod health checks, and root cause trace analysis.

## Team Members

| Name | Role |
|------|------|
| Sabyasachi Choudhury | Team Lead / Architect |
| Pankaj Dhondiba | Developer |
| Priyanka Deovrat Dongre | Developer |

## Project

All source code, agent configuration, and documentation is in the [`perfbot-hackathon/`](perfbot-hackathon/) folder:

| Folder | Contents |
|--------|----------|
| [`azure-function/`](perfbot-hackathon/azure-function/) | Azure Function proxy (3 endpoints: metrics, pods, traces) |
| [`foundry-agent/`](perfbot-hackathon/foundry-agent/) | Agent system prompt (349 lines) + 3 OpenAPI tool specs |
| [`foundry-sdk/`](perfbot-hackathon/foundry-sdk/) | SDK sample to invoke PerfBot programmatically |
| [`docs/`](perfbot-hackathon/docs/) | Architecture diagram + setup guide |
| [`demo/`](perfbot-hackathon/demo/) | Presentation deck + demo script |

## Quick Links

- **Full README:** [perfbot-hackathon/README.md](perfbot-hackathon/README.md)
- **Architecture:** [perfbot-hackathon/docs/architecture.md](perfbot-hackathon/docs/architecture.md)
- **Demo Script:** [perfbot-hackathon/demo/demo-script.md](perfbot-hackathon/demo/demo-script.md)
- **Presentation:** [perfbot-hackathon/demo/PerfBot-Hackathon-Deck.pptx](perfbot-hackathon/demo/PerfBot-Hackathon-Deck.pptx)
