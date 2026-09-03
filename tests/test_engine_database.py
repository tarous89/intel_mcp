from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
import re
from typing import Any

import pytest

from intel_mcp.config import ENGINE_READER_ROLE, Settings
from intel_mcp.engine_database import DatabaseEngineClient


def database_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_control_url": "https://intel.example.test",
        "app_service_token": "test-app-token",
        "engine_api_url": "https://engine.example.test",
        "engine_service_token": "test-engine-token",
        "mcp_inbound_service_token": "test-mcp-token",
        "allowed_hosts": ("localhost",),
        "port": 8000,
        "request_timeout_seconds": 1,
        "engine_source": "database",
        "engine_database_host": "engine-db.internal",
        "engine_database_name": "intel",
        "engine_database_user": ENGINE_READER_ROLE,
        "engine_database_password": "correct horse battery staple 123456",
    }
    values.update(overrides)
    return Settings(**values)


def test_database_source_requires_exact_restricted_login() -> None:
    database_settings().validate_engine()

    with pytest.raises(RuntimeError, match=ENGINE_READER_ROLE):
        database_settings(engine_database_user="database_owner").validate_engine()

    with pytest.raises(RuntimeError, match=ENGINE_READER_ROLE):
        database_settings(
            engine_database_url="postgresql://database_owner:secret@db/internal"
        ).validate_engine()


def test_database_dsn_encodes_credentials_and_defaults_to_tls() -> None:
    settings = database_settings(engine_database_password="a secret/with?reserved#characters")

    dsn = settings.engine_database_dsn()

    assert dsn.startswith(f"postgresql://{ENGINE_READER_ROLE}:")
    assert "a%20secret%2Fwith%3Freserved%23characters" in dsn
    assert dsn.endswith("?sslmode=require")


class FakeConnection:
    def __init__(self) -> None:
        self.events: list[str] = []

    def transaction(self):
        return nullcontext()

    def execute(self, statement: str):
        self.events.append(statement)


class FakePool:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection_value = connection

    def connection(self, **_kwargs: Any):
        return nullcontext(self.connection_value)


def test_every_database_read_starts_with_transaction_read_only() -> None:
    connection = FakeConnection()
    client = DatabaseEngineClient(
        database_settings(),
        pool=FakePool(connection),  # type: ignore[arg-type]
    )

    result = client._execute(
        lambda active, request: (
            active.events.append("READ FUNCTION"),
            request,
        )[1],  # type: ignore[arg-type]
        {"trial_id": "2024-500001-00-00"},
    )

    assert result == {"trial_id": "2024-500001-00-00"}
    assert connection.events == ["SET TRANSACTION READ ONLY", "READ FUNCTION"]


def test_local_engine_read_code_contains_no_write_statements() -> None:
    root = Path(__file__).parents[1] / "src/intel_mcp/engine_read"
    source = "\n".join(path.read_text() for path in root.glob("*.py"))

    write_sql = re.compile(
        r"\b(?:INSERT\s+INTO|DELETE\s+FROM|UPDATE\s+[a-z_.]+\s+SET|"
        r"TRUNCATE\s+(?:TABLE\s+)?|DROP\s+(?:TABLE|SCHEMA))\b",
        re.IGNORECASE,
    )
    assert not write_sql.search(source)
    assert "mcp_serving.approved_profiles_v1" in source
    assert "mcp_serving.profile_filter_v1" in source
