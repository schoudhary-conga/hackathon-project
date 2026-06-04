# PerfBot — PowerPoint Deck Outline

Use this to create your final demo deck. Each section = 1 slide.

---

## Slide 1: Title

**PerfBot — AI-Powered Performance Insights via Microsoft Teams**

- SPARK Global AI Hackathon | June 3–4, 2026
- Team: **Perf Alchemists**
- Category: AI in Engineering
- AI Tool: Azure AI Foundry

**Team Members:**
- Sabyasachi Choudhury (Team Lead)
- Pankaj Dhondiba
- Priyanka Deovrat Dongre

---

## Slide 2: The Problem

**Title:** The Problem — Performance Data is Locked Behind Tribal Knowledge

- After every K6 test run, engineers spend **15–30 minutes** manually querying Grafana/InfluxDB
- Requires knowledge of: Flux query syntax, metric names, service mappings, historical baselines
- Only **2–3 people** on the team can effectively interpret results
- Creates bottleneck: PMs, QA, and developers can't self-serve

**Visual:** Screenshot of complex Grafana dashboard / Flux query (show the pain)

---

## Slide 3: The Solution

**Title:** PerfBot — Ask a Question, Get an Answer

- A Microsoft Teams bot that answers natural-language questions about performance results
- Powered by **Azure AI Foundry** (GPT-4o v35)
- 3 tools: Metrics (InfluxDB) + Pod Health (Kubernetes) + Trace RCA (Grafana Tempo)

**Example:**
> User: "Did platform-data-api pass SLA in the last run?"
> Bot: "⚠️ BREACH — 5/6 endpoints PASS. 304_DocMgt: p95 = 54,190ms → SLA BREACH. CRUD endpoints: all < 310ms → PASS."

**Visual:** Screenshot of Teams conversation with PerfBot response

---

## Slide 4: Architecture

**Title:** How It Works — Simple & Elegant

```
Teams → Azure AI Foundry Agent (GPT-4o v35) → Azure Function → InfluxDB / Kubernetes / Grafana Tempo
```

- **Agent**: Parses intent, picks tool, generates queries, interprets results
- **Azure Function**: Python 3.13 proxy with 3 endpoints (/api/query, /api/pods, /api/trace)
- **System Prompt**: 349 lines encoding all domain knowledge (service mappings, SLA rules, Flux templates)

**Key Insight:** No custom backend, no database, no web app — just Foundry + one Function

**Visual:** Architecture diagram (Mermaid from docs/architecture.md)

---

## Slide 5: Capabilities

**Title:** What PerfBot Can Do

| Capability | Example Question |
|------------|-----------------|
| Quick Status | "How did platform-data-api do?" |
| Pass/Fail | "Did last night's run pass?" |
| All Services Scan | "Any failures today?" |
| Build Comparison | "Compare build X vs Y" |
| Per-API Drill-down | "Which APIs are slowest?" |
| Regression Detection | "What regressed?" |
| SLA Check | "Is it within SLA?" |
| Grafana Links | "Show me the Grafana link" |
| Pod Health | "Are pods healthy?" |
| Root Cause (Trace) | "Why is this API slow?" |
| Expert Analysis | "Is it safe to deploy?" |

---

## Slide 6: Live Demo (or Video)

**Title:** Demo

- Show Teams interaction
- Ask 2–3 questions, show responses
- Highlight: speed (5 seconds), clarity (natural language), depth (expert reasoning)

*(Embed video or do live demo)*

---

## Slide 7: Business Value & ROI

**Title:** Impact

| Metric | Before | After |
|--------|--------|-------|
| Time to insight | 15–30 min | **5 seconds** |
| Who can access | 2–3 engineers | **Entire team** |
| Regression detection | Manual, next-day | **Immediate** |
| Grafana expertise needed | Yes | **No** |

**ROI:**
- **~5 engineering hours/week saved** (15 min × 20 queries/week)
- **Faster feedback loop** → fewer degraded builds shipped
- **Reduced onboarding time** → new members ask bot instead of learning Flux
- **Democratized access** → PMs, QA, devs self-serve

---

## Slide 8: What's Next (Future Vision)

- Proactive alerts: Bot pushes regression summaries when runs complete
- CPU/Memory monitoring: Resource utilization insights per service
- Trend analysis: "Show me the last 5 runs" → trend charts
- Integration with Jira: Auto-create tickets for breaches
- Multi-service risk ranking & priorities

---

## Slide 9: Thank You

**Team Perf Alchemists**
- Sabyasachi Choudhury
- Pankaj Dhondiba
- Priyanka Deovrat Dongre

**Links:**
- GitHub Repo: [your-repo-url]
- Azure AI Foundry Project: perf-alchemists-project
- Bot in Teams: PerfBot
