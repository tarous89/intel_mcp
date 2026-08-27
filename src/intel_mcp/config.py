from __future__ import annotations

import os
from dataclasses import dataclass


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_control_url: str
    app_service_token: str
    engine_api_url: str
    engine_service_token: str
    mcp_inbound_service_token: str
    allowed_hosts: tuple[str, ...]
    port: int
    request_timeout_seconds: float
    openai_api_key: str
    openai_base_url: str
    classifier_model: str
    classifier_reasoning_effort: str
    classifier_service_tier: str
    classifier_max_output_tokens: int
    classifier_concurrency: int
    classifier_timeout_seconds: float

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            app_control_url=os.getenv("INTEL_APP_CONTROL_URL", "").strip().rstrip("/"),
            app_service_token=os.getenv("INTEL_APP_SERVICE_TOKEN", "").strip(),
            engine_api_url=os.getenv("INTEL_ENGINE_API_URL", "").strip().rstrip("/"),
            engine_service_token=os.getenv("INTEL_ENGINE_SERVICE_TOKEN", "").strip(),
            mcp_inbound_service_token=os.getenv("MCP_INBOUND_SERVICE_TOKEN", "").strip(),
            allowed_hosts=_csv(
                os.getenv(
                    "MCP_ALLOWED_HOSTS",
                    "127.0.0.1,127.0.0.1:*,localhost,localhost:*,[::1],[::1]:*",
                )
            ),
            port=int(os.getenv("PORT", "8000")),
            request_timeout_seconds=float(os.getenv("INTEL_APP_REQUEST_TIMEOUT_SECONDS", "10")),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/"),
            classifier_model=os.getenv("MCP_CLASSIFIER_MODEL", "gpt-5.6-terra").strip(),
            classifier_reasoning_effort=os.getenv("MCP_CLASSIFIER_REASONING_EFFORT", "high").strip(),
            classifier_service_tier=os.getenv("MCP_CLASSIFIER_SERVICE_TIER", "standard").strip(),
            classifier_max_output_tokens=int(os.getenv("MCP_CLASSIFIER_MAX_OUTPUT_TOKENS", "12000")),
            classifier_concurrency=max(1, min(8, int(os.getenv("MCP_CLASSIFIER_CONCURRENCY", "4")))),
            classifier_timeout_seconds=float(os.getenv("MCP_CLASSIFIER_TIMEOUT_SECONDS", "300")),
        )

    def validate_control_plane(self) -> None:
        if not self.app_control_url:
            raise RuntimeError("INTEL_APP_CONTROL_URL is not configured")
        if not self.app_service_token:
            raise RuntimeError("INTEL_APP_SERVICE_TOKEN is not configured")

    def validate_inbound_auth(self) -> None:
        if not self.mcp_inbound_service_token:
            raise RuntimeError("MCP_INBOUND_SERVICE_TOKEN is not configured")

    def validate_engine(self) -> None:
        if not self.engine_api_url:
            raise RuntimeError("INTEL_ENGINE_API_URL is not configured")
        if not self.engine_service_token:
            raise RuntimeError("INTEL_ENGINE_SERVICE_TOKEN is not configured")

    def validate_classifier(self) -> None:
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if not self.classifier_model:
            raise RuntimeError("MCP_CLASSIFIER_MODEL is not configured")
        if self.classifier_max_output_tokens < 1:
            raise RuntimeError("MCP_CLASSIFIER_MAX_OUTPUT_TOKENS must be positive")
