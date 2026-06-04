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
- Powered by **Azure AI Foundry** (GPT-4o)
- Queries live InfluxDB data — no manual work needed

**Example:**
> User: "How did platform-data-api do in the last run?"
> Bot: "✅ PASS — all endpoints under SLA. p95: 847ms. No regressions vs baseline."

**Visual:** Screenshot of Teams conversation with PerfBot response

---

## Slide 4: Architecture

**Title:** How It Works — Simple & Elegant

```
Teams → Azure AI Foundry Agent (GPT-4o) → Azure Function → InfluxDB
```

- **Agent**: Parses intent, generates Flux queries, interprets results
- **Azure Function**: 75-line Python proxy that bridges Foundry → InfluxDB
- **System Prompt**: 231 lines encoding all domain knowledge (service mappings, SLA rules, Flux templates)

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
- Trend analysis: "Show me the last 5 runs" → trend charts
- Integration with Jira: Auto-create tickets for breaches
- Root cause suggestions: "The regression correlates with deployment X"

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
