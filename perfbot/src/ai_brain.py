"""LLM integration for intent parsing and insight generation (Azure OpenAI or Ollama)."""

from openai import AsyncAzureOpenAI, AsyncOpenAI

from src.config import settings
from src.constants import SERVICE_ALIASES, SERVICE_MAPPINGS

SYSTEM_PROMPT = """You are PerfBot, an AI assistant that helps engineers understand K6 performance test results.

You have access to an InfluxDB database with K6 metrics. Your job is to:
1. Understand WHAT the user actually wants to know — not just the topic, but the depth
2. Parse the user's natural language question into a structured intent
3. Resolve service names to their correct testName in InfluxDB
4. Determine the appropriate response style based on the user's actual need

## Known Service Mappings (folder name → InfluxDB testName):
- platform-data-api → platform-objectdb-api
- platform-scheduler-api → platform-scheduler-api
- platform-configuration-mgmt-api → platform-configuration-mgmt-api
- contract-api → contract-api
- dc-ui → dc-ui

## Fuzzy Aliases:
- "platform data" / "PDA" / "objectdb" → platform-objectdb-api
- "scheduler" → platform-scheduler-api
- "dc ui" / "dcui" / "partner commerce" → dc-ui
- "config management" / "config mgmt" → platform-configuration-mgmt-api
- "contract" → contract-api

## Important Rules:
- InfluxDB org is "performance" (NEVER "conga")
- Values are stored as strings — always use toFloat() before aggregation
- Exclude setup calls: getBuildId, generateClientCredentialsToken
- "last run" = max(buildId), "previous" = second-latest buildId
- Grafana links must include &from=<epoch_ms>&to=<epoch_ms>

## Intent Types:
- general_info: General/FAQ questions that do NOT need InfluxDB data ("what is PDA?", "what services do you track?", "help", "what can you do?")
- quick_status: General "how did X do?" questions
- pass_fail: "Did it pass?" questions
- all_services_scan: "Any failures?" across all services
- comparison: "Compare build X vs Y"
- trends: "Show last N runs"
- drill_down: "Which APIs are slowest?"
- regressions: "What regressed?"
- sla_check: "Is X within SLA?"
- active_runs: "Is anything running?"
- grafana_link: "Show Grafana link"

IMPORTANT: Use "general_info" for ANY question that can be answered from your system knowledge without querying metrics data. Examples: "what is PDA?", "what services exist?", "what do you do?", "explain SLA", "what is p95?".

## Response Style (CRITICAL — think about what the user actually wants):
Determine whether the user wants a BRIEF conversational answer or a DETAILED data-heavy response.

Use "brief" when the user:
- Asks a yes/no question ("Did it pass?", "Is it healthy?", "Any issues?")
- Wants a conclusion or summary ("How did it go?", "What's the verdict?")
- Asks a simple factual question ("What was the p95?", "How many errors?")
- Wants a quick answer they can act on ("Should I be worried?", "Is it safe to deploy?")
- Asks "why" questions ("Why did it fail?", "What caused the regression?")
- Uses casual/brief phrasing ("pda status?", "scheduler ok?")

Use "detailed" when the user:
- Explicitly asks for data ("Show me the numbers", "Give me the full breakdown")
- Asks to compare specific builds ("Compare build X vs Y")
- Requests a drill-down ("Which APIs are slowest?", "Show per-API metrics")
- Asks for trends ("Show last 5 runs")
- Requests a chart or graph ("Show me a graph")
- Asks for a Grafana link

Respond ONLY with valid JSON in this format:
{
  "intent": "<intent_type>",
  "service": "<resolved_testName or null>",
  "build_id": "<specific build or null>",
  "compare_build_id": "<comparison build or null>",
  "count": <number for trends or null>,
  "response_style": "<brief or detailed>",
  "raw_query": "<original user question>"
}
"""


class AIBrain:
    """LLM-powered intent parser and response generator (Azure OpenAI or Ollama)."""

    def __init__(self):
        if settings.llm_provider == "ollama":
            self.client = AsyncOpenAI(
                base_url=settings.ollama_base_url,
                api_key="ollama",  # Ollama doesn't require a real key
            )
            self.model = settings.ollama_model
        elif settings.llm_provider == "azure_foundry":
            # Azure AI Foundry — standard OpenAI client with base_url
            self.client = AsyncOpenAI(
                base_url=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
            )
            self.model = settings.azure_openai_deployment
        else:
            self.client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            self.model = settings.azure_openai_deployment

    async def parse_intent(self, user_message: str) -> dict:
        """Parse user message into structured intent."""
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.0,
        }
        # json_object response format may not be supported by all Ollama models
        if settings.llm_provider != "ollama":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)

        import json
        try:
            result = json.loads(response.choices[0].message.content)
        except (json.JSONDecodeError, IndexError):
            result = {
                "intent": "quick_status",
                "service": None,
                "raw_query": user_message,
            }

        # Fallback resolution if LLM didn't resolve
        if not result.get("service"):
            result["service"] = self._resolve_service(user_message)

        return result

    async def generate_insight(self, metrics: dict, comparison: dict | None = None) -> str:
        """Generate a natural language insight from metrics data."""
        prompt = f"""Given these performance metrics, write a 1-2 sentence insight:

Current metrics: {metrics}
{"Comparison with baseline: " + str(comparison) if comparison else "No baseline comparison available."}

Focus on: what passed/failed, biggest regression, actionable takeaway.
Keep it concise and technical."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a performance engineering expert. Be concise."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()

    async def generate_conversational_response(self, user_query: str, metrics: dict, comparison: dict | None = None) -> str:
        """Generate a direct conversational answer to the user's question based on metrics data.

        Instead of dumping all data, this answers the actual question concisely.
        """
        prompt = f"""The user asked: "{user_query}"

Here is the performance data I have:
- Metrics: {metrics}
{"- Comparison with baseline: " + str(comparison) if comparison else ""}

INSTRUCTIONS:
- Answer the user's ACTUAL question directly. Do not dump all available data.
- If they asked "did it pass?" → answer yes/no with a one-line reason.
- If they asked "how did it go?" → give the verdict and ONE key highlight (best/worst).
- If they asked "any issues?" → list only the issues, or say "no issues".
- If they asked "should I worry?" → give a clear recommendation.
- If they asked "why did it fail?" → identify the root cause from the data.
- Keep the answer to 2-4 sentences MAX. Be conversational, not robotic.
- Use specific numbers when relevant but don't list every endpoint.
- If everything looks good, say so clearly and briefly.
- End with a suggestion ONLY if there's something actionable (e.g., "Want the full breakdown?" or "I can show the per-API details if you need them.")"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are PerfBot, a helpful performance engineering assistant. "
                 "You answer questions directly and conversationally — like a senior engineer on Slack. "
                 "You do NOT dump tables or raw data unless explicitly asked. "
                 "You focus on conclusions, verdicts, and actionable takeaways."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()

    def _resolve_service(self, text: str) -> str | None:
        """Attempt to resolve service name from text using known aliases."""
        text_lower = text.lower()
        for alias, test_name in SERVICE_ALIASES.items():
            if alias in text_lower:
                return test_name
        for name, test_name in SERVICE_MAPPINGS.items():
            if name in text_lower:
                return test_name
        return None


ai_brain = AIBrain()
