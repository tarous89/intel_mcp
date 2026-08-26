from __future__ import annotations

import os
from dataclasses import dataclass


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_control_url: str
    app_service_token: str
    allowed_hosts: tuple[str, ...]
    port: int
    request_timeout_seconds: float

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            app_control_url=os.getenv("INTEL_APP_CONTROL_URL", "").strip().rstrip("/"),
            app_service_token=os.getenv("INTEL_APP_SERVICE_TOKEN", "").strip(),
            allowed_hosts=_csv(
                os.getenv(
                    "MCP_ALLOWED_HOSTS",
                    "127.0.0.1,127.0.0.1:*,localhost,localhost:*,[::1],[::1]:*",
                )
            ),
            port=int(os.getenv("PORT", "8000")),
            request_timeout_seconds=float(os.getenv("INTEL_APP_REQUEST_TIMEOUT_SECONDS", "10")),
        )

    def validate_control_plane(self) -> None:
        if not self.app_control_url:
            raise RuntimeError("INTEL_APP_CONTROL_URL is not configured")
        if not self.app_service_token:
            raise RuntimeError("INTEL_APP_SERVICE_TOKEN is not configured")
