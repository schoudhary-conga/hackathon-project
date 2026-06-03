"""PerfBot configuration loaded from environment variables."""

import os

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure Bot Framework
    microsoft_app_id: str = ""
    microsoft_app_password: str = ""
    microsoft_app_tenant_id: str = ""

    # LLM Provider: "azure_openai" or "ollama"
    llm_provider: str = "ollama"

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-12-01-preview"

    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1:8b"

    # InfluxDB
    influxdb_url: str = "http://20.252.97.68:80"
    influxdb_org: str = "performance"
    influxdb_token: str = ""
    influxdb_bucket: str = "k6"

    # Grafana
    grafana_base_url: str = "https://engr-telemetry.conga-panoptos.com"

    # Teams proactive alerts
    teams_webhook_url: str = ""

    # Server
    port: int = 3978

    @model_validator(mode="after")
    def _fallback_k6_env_vars(self):
        """Accept K6_ prefixed env vars as used in the perf cluster."""
        if not self.influxdb_token:
            self.influxdb_token = os.environ.get("K6_INFLUXDB_TOKEN", "")
        if not self.influxdb_url or self.influxdb_url == "http://20.252.97.68:80":
            self.influxdb_url = os.environ.get("K6_INFLUXDB_ADDR", self.influxdb_url)
        k6_org = os.environ.get("K6_INFLUXDB_ORGANIZATION", "")
        if k6_org and not os.environ.get("INFLUXDB_ORG"):
            self.influxdb_org = k6_org
        k6_bucket = os.environ.get("K6_INFLUXDB_BUCKET", "")
        if k6_bucket and not os.environ.get("INFLUXDB_BUCKET"):
            self.influxdb_bucket = k6_bucket
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
