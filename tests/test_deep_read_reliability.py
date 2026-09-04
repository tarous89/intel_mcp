from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from intel_mcp.classification import TerraClassifier
from intel_mcp.config import Settings, _openai_service_tier
from intel_mcp.engine_read.document_retrieval import get_approved_document_text
from intel_mcp.engine_read.extraction_source import get_approved_extraction_source
from intel_mcp.extraction import ExtractionVariable, TerraExtractor


class FakeResult:
    def __init__(self, *, one: tuple[Any, ...] | None = None, many: list[tuple[Any, ...]] | None = None) -> None:
        self._one = one
        self._many = many or []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many


class SequencedConnection:
    def __init__(self, results: list[FakeResult]) -> None:
        self.results = list(results)
        self.statements: list[str] = []
        self.params: list[tuple[Any, ...] | None] = []

    def execute(self, statement: str, params: tuple[Any, ...] | None = None):
        self.statements.append(" ".join(statement.split()))
        self.params.append(params)
        if not self.results:
            raise AssertionError("Unexpected SQL statement")
        return self.results.pop(0)


def _profile(protocol_name: str = "Protocol") -> dict[str, Any]:
    return {
        "filtering_variables": {
            "available_extracted_documents": {
                "protocol": [protocol_name],
                "recruitment_arrangements": [],
                "patient_information_and_informed_consent": [],
                "assessments_and_forms": [],
                "clinical_study_report": [],
                "results_summary": [],
            }
        }
    }


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_control_url": "https://intel.example.test",
        "app_service_token": "app-token",
        "engine_api_url": "https://engine.example.test",
        "engine_service_token": "engine-token",
        "mcp_inbound_service_token": "mcp-token",
        "allowed_hosts": ("localhost",),
        "port": 8000,
        "request_timeout_seconds": 1,
        "openai_api_key": "test-key",
    }
    values.update(overrides)
    return Settings(**values)


def test_legacy_standard_service_tier_is_normalized_and_report_workers_default_to_flex() -> None:
    assert _openai_service_tier("standard") == "default"
    assert _openai_service_tier(" DEFAULT ") == "default"
    assert _openai_service_tier(" flex ") == "flex"
    assert Settings.__dataclass_fields__["classifier_service_tier"].default == "flex"
    assert Settings.__dataclass_fields__["extractor_service_tier"].default == "flex"


@pytest.mark.anyio
async def test_classifier_sends_flex_service_tier() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["service_tier"] == "flex"
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "trial_id": "2024-500001-00-00",
                                        "inclusion_results": [
                                            {
                                                "criterion_id": "i1",
                                                "classification": True,
                                                "evidence": "Supported by the profile.",
                                            }
                                        ],
                                        "exclusion_results": [
                                            {
                                                "criterion_id": "e1",
                                                "classification": False,
                                                "evidence": "Not present in the profile.",
                                            }
                                        ],
                                    }
                                ),
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
            },
        )

    classifier = TerraClassifier(_settings(), transport=httpx.MockTransport(handler))
    result = await classifier.classify(
        trial_id="2024-500001-00-00",
        profile=_profile(),
        inclusion_criteria=["The trial includes adults"],
        exclusion_criteria=["The trial is restricted to healthy volunteers"],
    )
    assert result.trial_id == "2024-500001-00-00"


@pytest.mark.anyio
async def test_extractor_sends_flex_service_tier() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["service_tier"] == "flex"
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps({"values": {"phase_label": "Phase 2"}}),
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
            },
        )

    extractor = TerraExtractor(_settings(), transport=httpx.MockTransport(handler))
    values = await extractor.extract(
        trial_id="2024-500001-00-00",
        profile=_profile(),
        protocol_text="Phase 2 trial.",
        variables=[
            ExtractionVariable(
                name="phase_label",
                instruction="Return the protocol phase label.",
                value_type="string",
            )
        ],
    )
    assert values == {"phase_label": "Phase 2"}


def test_document_retrieval_resolves_catalogue_then_reads_exact_text_row() -> None:
    connection = SequencedConnection(
        [
            FakeResult(one=(_profile(),)),
            FakeResult(
                many=[
                    (7, "uuid-7", "protocol", "Protocol", "Protocol", "protocol.pdf"),
                ]
            ),
            FakeResult(one=("Protocol body", [])),
        ]
    )

    result = get_approved_document_text(
        connection,  # type: ignore[arg-type]
        {
            "trial_id": "2024-500001-00-00",
            "document_name": "Protocol",
            "part": 1,
        },
    )

    assert result["document_name"] == "Protocol"
    assert "Protocol body" in result["text"]
    assert connection.params[-1] == (7,)
    assert "WHERE document_id = %s" in connection.statements[-1]
    assert not any(
        "mcp_serving.documents_v1" in statement
        and "mcp_serving.document_text_v1" in statement
        for statement in connection.statements
    )


def test_extraction_source_resolves_protocol_then_reads_exact_text_row() -> None:
    connection = SequencedConnection(
        [
            FakeResult(one=(_profile(), 42)),
            FakeResult(many=[(7, "Protocol", "protocol.pdf", "Protocol")]),
            FakeResult(one=("Protocol body", [])),
        ]
    )

    result = get_approved_extraction_source(
        connection,  # type: ignore[arg-type]
        {"trial_id": "2024-500001-00-00"},
    )

    assert result["protocol_text"] == "Protocol body"
    assert connection.params[-1] == (7,)
    assert "WHERE document_id = %s" in connection.statements[-1]
    assert not any(
        "mcp_serving.documents_v1" in statement
        and "mcp_serving.document_text_v1" in statement
        for statement in connection.statements
    )
