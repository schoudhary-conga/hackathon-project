# Foundry SDK — Run PerfBot Agent Programmatically

This folder contains the Azure AI Foundry SDK sample code for invoking the PerfBot agent outside of Teams/Web Chat (e.g., from a script, CI pipeline, or custom app).

## Prerequisites

- Python 3.10+
- Azure CLI logged in (`az login`)
- Access to the `perf-alchemists-project` in Azure AI Foundry

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your subscription ID in .env
```

## Run

```bash
python run_agent.py
```

This will:
1. Authenticate via `DefaultAzureCredential` (uses your Azure CLI session)
2. Connect to the PerfBot agent (version 35) in Foundry
3. Send a sample message and print the response

## Customizing

Edit the `input` in `run_agent.py` to ask any performance question:

```python
response = openai_client.responses.create(
    input=[{"role": "user", "content": "Did platform-objectdb-api pass SLA in the last run?"}],
    extra_body={"agent_reference": {"name": my_agent, "version": my_version, "type": "agent_reference"}},
)
```

## Deploy as Web App

To scaffold and deploy a full web app around this agent:

```bash
azd init -t https://github.com/Azure-Samples/get-started-with-ai-agents
azd up
```

To tear down:
```bash
azd down
```
