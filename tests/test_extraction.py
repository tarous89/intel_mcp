from __future__ import annotations

import json

import httpx
import pytest

from intel_mcp.config import Settings
from intel_mcp.extraction import (
    ExtractionVariable,
    ExtractorError,
    TerraExtractor,
    extraction_key,
    normalize_variables,
    result_schema,
    validate_worker_values,
)


def settings() -> Settings:
    return Settings(
        app_control_url="https://intel.example.test",
        app_service_token="test-app-token",
        engine_api_url="https://engine.example.test",
        engine_service_token="test-engine-token",
        mcp_inbound_service_token="test-mcp-token",
        allowed_hosts=("localhost",),
        port=8000,
        request_timeout_seconds=1,
        openai_api_key="test-openai-key",
    )


def variables() -> list[ExtractionVariable]:
    return [
        ExtractionVariable(
            name="planned_sample_size",
            instruction="Return the planned randomized population.",
            value_type="integer",
        ),
        ExtractionVariable(
            name="central_imaging_review",
            instruction="Is central imaging review required?",
            value_type="boolean",
        ),
    ]


def test_worker_schema_contains_values_only() -> None:
    schema = result_schema(variables())
    assert set(schema["properties"]) == {"values"}
    value_properties = schema["properties"]["values"]["properties"]
    assert set(value_properties) == {"planned_sample_size", "central_imaging_review"}
    assert not {
        "status",
        "explanation",
        "source",
        "document_name",
        "page",
    } & set(value_properties)


def test_variable_names_are_unique_and_fingerprint_ignores_order() -> None:
    first = variables()
    second = list(reversed(first))
    assert extraction_key("2024-500001-00-00", first) == extraction_key(
        "2024-500001-00-00", second
    )
    with pytest.raises(ValueError):
        normalize_variables([first[0], first[0]])


def test_worker_validation_accepts_null_and_rejects_wrong_types() -> None:
    assert validate_worker_values(
        {
            "values": {
                "planned_sample_size": 420,
                "central_imaging_review": None,
            }
        },
        variables(),
    ) == {
        "planned_sample_size": 420,
        "central_imaging_review": None,
    }
    with pytest.raises(ExtractorError):
        validate_worker_values(
            {
                "values": {
                    "planned_sample_size": "420",
                    "central_imaging_review": None,
                }
            },
            variables(),
        )


@pytest.mark.anyio
async def test_terra_extractor_sends_profile_and_protocol_in_one_request() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        payload = json.loads(request.content)
        user_payload = json.loads(payload["input"][1]["content"][0]["text"])
        assert user_payload["trial_profile"] == {"planned_sample_size": 420}
        assert user_payload["protocol_text"] == "Complete protocol"
        assert set(payload["text"]["format"]["schema"]["properties"]) == {"values"}
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
                                        "values": {
                                            "planned_sample_size": 420,
                                            "central_imaging_review": None,
                                        }
                                    }
                                ),
                            }
                        ],
                    }
                ],
            },
        )

    result = await TerraExtractor(
        settings(), transport=httpx.MockTransport(handler)
    ).extract(
        trial_id="2024-500001-00-00",
        profile={"planned_sample_size": 420},
        protocol_text="Complete protocol",
        variables=variables(),
    )

    assert calls == 1
    assert result["planned_sample_size"] == 420
    assert result["central_imaging_review"] is None
