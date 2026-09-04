from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit


ENGINE_READER_ROLE = "intel_mcp_reader_v1"


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _openai_service_tier(value: str) -> str:
    """Normalize legacy human wording to a valid Responses API service tier.

    Earlier MCP deployments used ``standard`` as an internal pricing label, but the
    Responses API uses ``default`` for standard processing. Keep accepting the old
    environment value so production self-heals without a coordinated secret change.
    """
    normalized = value.strip().casefold()
    if not normalized or normalized == "standard":
        return "default"
    return normalized


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
    report_plan_service_token: str = ""
    engine_source: str = "http"
    engine_database_url: str = ""
    engine_database_host: str = ""
    engine_database_port: int = 5432
    engine_database_name: str = ""
    engine_database_user: str = ENGINE_READER_ROLE
    engine_database_password: str = ""
    engine_database_sslmode: str = "require"
    engine_database_pool_size: int = 5
    mcp_public_resource_url: str = "https://mcp.trialagents.com/mcp"
    oauth_authorization_server_url: str = "https://intel.trialagents.com"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    classifier_model: str = "gpt-5.6-terra"
    classifier_reasoning_effort: str = "high"
    classifier_service_tier: str = "default"
    classifier_max_output_tokens: int = 12000
    classifier_concurrency: int = 4
    classifier_timeout_seconds: float = 300
    extractor_model: str = "gpt-5.6-terra"
    extractor_reasoning_effort: str = "high"
    extractor_service_tier: str = "default"
    extractor_max_output_tokens: int = 12000
    extractor_timeout_seconds: float = 300

    @classmethod
    def from_environment(cls) -> "Settings":
        engine_database_url = os.getenv("MCP_ENGINE_DATABASE_URL", "").strip()
        engine_database_host = os.getenv("MCP_ENGINE_DATABASE_HOST", "").strip()
        configured_source = os.getenv("MCP_ENGINE_SOURCE", "").strip().casefold()
        engine_source = configured_source or (
            "database" if engine_database_url or engine_database_host else "http"
        )
        return cls(
            app_control_url=os.getenv("INTEL_APP_CONTROL_URL", "").strip().rstrip("/"),
            app_service_token=os.getenv("INTEL_APP_SERVICE_TOKEN", "").strip(),
            engine_api_url=os.getenv("INTEL_ENGINE_API_URL", "").strip().rstrip("/"),
            engine_service_token=os.getenv("INTEL_ENGINE_SERVICE_TOKEN", "").strip(),
            mcp_inbound_service_token=os.getenv("MCP_INBOUND_SERVICE_TOKEN", "").strip(),
            report_plan_service_token=os.getenv("REPORT_PLAN_SERVICE_TOKEN", "").strip(),
            mcp_public_resource_url=os.getenv(
                "MCP_PUBLIC_RESOURCE_URL", "https://mcp.trialagents.com/mcp"
            ).strip().rstrip("/"),
            oauth_authorization_server_url=os.getenv(
                "MCP_OAUTH_AUTHORIZATION_SERVER_URL", "https://intel.trialagents.com"
            ).strip().rstrip("/"),
            allowed_hosts=_csv(
                os.getenv(
                    "MCP_ALLOWED_HOSTS",
                    "127.0.0.1,127.0.0.1:*,localhost,localhost:*,[::1],[::1]:*",
                )
            ),
            port=int(os.getenv("PORT", "8000")),
            request_timeout_seconds=float(os.getenv("INTEL_APP_REQUEST_TIMEOUT_SECONDS", "10")),
            engine_source=engine_source,
            engine_database_url=engine_database_url,
            engine_database_host=engine_database_host,
            engine_database_port=int(os.getenv("MCP_ENGINE_DATABASE_PORT", "5432")),
            engine_database_name=os.getenv("MCP_ENGINE_DATABASE_NAME", "").strip(),
            engine_database_user=os.getenv(
                "MCP_ENGINE_DATABASE_USER", ENGINE_READER_ROLE
            ).strip(),
            engine_database_password=os.getenv(
                "MCP_ENGINE_DATABASE_PASSWORD", ""
            ),
            engine_database_sslmode=os.getenv(
                "MCP_ENGINE_DATABASE_SSLMODE", "require"
            ).strip(),
            engine_database_pool_size=max(
                1, min(10, int(os.getenv("MCP_ENGINE_DATABASE_POOL_SIZE", "5")))
            ),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/"),
            classifier_model=os.getenv("MCP_CLASSIFIER_MODEL", "gpt-5.6-terra").strip(),
            classifier_reasoning_effort=os.getenv("MCP_CLASSIFIER_REASONING_EFFORT", "high").strip(),
            classifier_service_tier=_openai_service_tier(
                os.getenv("MCP_CLASSIFIER_SERVICE_TIER", "default")
            ),
            classifier_max_output_tokens=int(os.getenv("MCP_CLASSIFIER_MAX_OUTPUT_TOKENS", "12000")),
            classifier_concurrency=max(1, min(8, int(os.getenv("MCP_CLASSIFIER_CONCURRENCY", "4")))),
            classifier_timeout_seconds=float(os.getenv("MCP_CLASSIFIER_TIMEOUT_SECONDS", "300")),
            extractor_model=os.getenv("MCP_EXTRACTOR_MODEL", "gpt-5.6-terra").strip(),
            extractor_reasoning_effort=os.getenv("MCP_EXTRACTOR_REASONING_EFFORT", "high").strip(),
            extractor_service_tier=_openai_service_tier(
                os.getenv("MCP_EXTRACTOR_SERVICE_TIER", "default")
            ),
            extractor_max_output_tokens=int(os.getenv("MCP_EXTRACTOR_MAX_OUTPUT_TOKENS", "12000")),
            extractor_timeout_seconds=float(os.getenv("MCP_EXTRACTOR_TIMEOUT_SECONDS", "300")),
        )

    def validate_control_plane(self) -> None:
        if not self.app_control_url:
            raise RuntimeError("INTEL_APP_CONTROL_URL is not configured")
        if not self.app_service_token:
            raise RuntimeError("INTEL_APP_SERVICE_TOKEN is not configured")

    def validate_inbound_auth(self) -> None:
        if not self.mcp_inbound_service_token:
            raise RuntimeError("MCP_INBOUND_SERVICE_TOKEN is not configured")

    def validate_report_plan(self) -> None:
        if not self.report_plan_service_token:
            raise RuntimeError("REPORT_PLAN_SERVICE_TOKEN is not configured")
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

    def validate_engine(self) -> None:
        if self.engine_source not in {"database", "http"}:
            raise RuntimeError("MCP_ENGINE_SOURCE must be database or http")
        if self.engine_source == "http":
            if not self.engine_api_url:
                raise RuntimeError("INTEL_ENGINE_API_URL is not configured")
            if not self.engine_service_token:
                raise RuntimeError("INTEL_ENGINE_SERVICE_TOKEN is not configured")
            return
        if self.engine_database_url:
            username = unquote(urlsplit(self.engine_database_url).username or "")
            if username != ENGINE_READER_ROLE:
                raise RuntimeError(
                    f"MCP_ENGINE_DATABASE_URL must use the restricted {ENGINE_READER_ROLE} login"
                )
            return
        missing = [
            name
            for name, value in (
                ("MCP_ENGINE_DATABASE_HOST", self.engine_database_host),
                ("MCP_ENGINE_DATABASE_NAME", self.engine_database_name),
                ("MCP_ENGINE_DATABASE_USER", self.engine_database_user),
                ("MCP_ENGINE_DATABASE_PASSWORD", self.engine_database_password),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing Engine database setting(s): {', '.join(missing)}")
        if self.engine_database_user != ENGINE_READER_ROLE:
            raise RuntimeError(
                f"MCP_ENGINE_DATABASE_USER must be {ENGINE_READER_ROLE}"
            )

    def engine_database_dsn(self) -> str:
        self.validate_engine()
        if self.engine_source != "database":
            raise RuntimeError("The Engine database is not the configured source")
        if self.engine_database_url:
            return self.engine_database_url
        user = quote(self.engine_database_user, safe="")
        password = quote(self.engine_database_password, safe="")
        host = self.engine_database_host
        database = quote(self.engine_database_name, safe="")
        sslmode = quote(self.engine_database_sslmode, safe="")
        return (
            f"postgresql://{user}:{password}@{host}:{self.engine_database_port}/"
            f"{database}?sslmode={sslmode}"
        )

    def validate_classifier(self) -> None:
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if not self.classifier_model:
            raise RuntimeError("MCP_CLASSIFIER_MODEL is not configured")
        if self.classifier_max_output_tokens < 1:
            raise RuntimeError("MCP_CLASSIFIER_MAX_OUTPUT_TOKENS must be positive")

    def validate_extractor(self) -> None:
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if not self.extractor_model:
            raise RuntimeError("MCP_EXTRACTOR_MODEL is not configured")
        if self.extractor_max_output_tokens < 1:
            raise RuntimeError("MCP_EXTRACTOR_MAX_OUTPUT_TOKENS must be positive")
