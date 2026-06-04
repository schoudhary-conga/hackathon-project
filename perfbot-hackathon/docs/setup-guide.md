# PerfBot — Setup Guide

Step-by-step instructions to recreate the PerfBot agent in Azure AI Foundry.

---

## Step 1: Create Azure AI Foundry Project

1. Go to [Azure AI Foundry](https://ai.azure.com)
2. Create a new project (or use existing: `perf-alchemists-project`)
3. Deploy **GPT-4o** model (Global Standard)

## Step 2: Create the Agent

1. In your project → **Agents** → **New Agent**
2. Name: `PerfBot`
3. Model: `gpt-4o`
4. Paste the full content of `foundry-agent/instructions.txt` into the Instructions field

## Step 3: Deploy Azure Function Proxy

The Azure Function acts as a bridge between Foundry and InfluxDB.

```bash
cd azure-function
func azure functionapp publish perfbot-influxdb-proxy
```

Or deploy via VS Code Azure Functions extension.

**Environment variables to set in Azure Function App Settings:**
- `INFLUXDB_URL`: `http://20.252.97.68:80`
- `INFLUXDB_TOKEN`: Your InfluxDB read token
- `RANCHER_BEARER_TOKEN`: Rancher API token for pod queries
- `TEMPO_API_KEY`: Grafana session cookie for Tempo trace API

## Step 4: Add OpenAPI Tools to Agent

1. In the agent → **Tools** → **Add** → **OpenAPI**
2. Upload `foundry-agent/openapi-influxdb.json` (InfluxDB metrics query)
3. Upload `foundry-agent/openapi-pods.json` (Kubernetes pod health)
4. Upload `foundry-agent/openapi-trace.json` (Grafana Tempo trace spans)
5. For each tool, create a **Connection**:
   - Auth type: API Key
   - Header name: `x-custom`
   - Value: any dummy value (Function handles auth internally)
6. Server URL should already be: `https://perfbot-influxdb-proxy-gxekcaa5chdwheaf.eastus2-01.azurewebsites.net`

## Step 5: Test in Playground

1. Open the agent in Foundry Playground
2. Ask: "How did platform-objectdb-api do in the last run?"
3. Verify the agent calls `query_influxdb` and returns metrics

## Step 6: Publish to Teams

1. Click **Publish** → **Teams and Microsoft 365 Copilot**
2. Follow the wizard (Foundry handles Bot Framework registration automatically)
3. Once published, find "PerfBot" in Teams Apps

## Step 7: (Optional) Run via SDK

```bash
cd foundry-sdk
pip install -r requirements.txt
python run_agent.py
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Agent says "tool not available" | Re-add the OpenAPI tool; check Connection is active |
| InfluxDB returns 400 | Ensure org is `performance` (not `conga`) |
| Empty results | Check testName mapping (e.g., `platform-data-api` folder → `platform-objectdb-api` in InfluxDB) |
| Function timeout | InfluxDB may be slow for large ranges; reduce `range(start: -7d)` |
