from __future__ import annotations

import json
import logging

import httpx
import pytest

from intel_mcp.openai_retry import post_openai_response


@pytest.mark.anyio
async def test_flex_capacity_429_retries_then_falls_back_to_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict[str, object]] = []
    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("intel_mcp.openai_retry.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("intel_mcp.openai_retry.random.uniform", lambda _start, _end: 0.0)

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        if payload["service_tier"] == "flex":
            return httpx.Response(
                429,
                headers={"Retry-After": "5", "x-request-id": f"req-{len(requests)}"},
                json={
                    "error": {
                        "message": "We're currently processing too many requests.",
                        "type": "invalid_request_error",
                        "code": "rate_limit_exceeded",
                    }
                },
            )
        return httpx.Response(200, json={"status": "completed"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await post_openai_response(
            client,
            url="https://api.openai.test/responses",
            headers={"Authorization": "Bearer test"},
            request={"model": "gpt-test", "service_tier": "flex"},
            logger=logging.getLogger("test"),
            operation="test operation",
        )

    assert response.status_code == 200
    assert [request["service_tier"] for request in requests] == [
        "flex",
        "flex",
        "flex",
        "flex",
        "auto",
    ]
    assert delays == [5.0, 5.0, 8.0]


@pytest.mark.anyio
async def test_non_transient_quota_429_is_not_retried() -> None:
    request_count = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            429,
            json={
                "error": {
                    "message": "Quota exhausted.",
                    "type": "insufficient_quota",
                    "code": "insufficient_quota",
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await post_openai_response(
            client,
            url="https://api.openai.test/responses",
            headers={"Authorization": "Bearer test"},
            request={"model": "gpt-test", "service_tier": "flex"},
            logger=logging.getLogger("test"),
            operation="test operation",
        )

    assert response.status_code == 429
    assert request_count == 1


@pytest.mark.anyio
async def test_output_token_incomplete_retries_once_with_larger_budget() -> None:
    requests: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            return httpx.Response(
                200,
                headers={"x-request-id": "req-incomplete"},
                json={
                    "id": "resp-incomplete",
                    "status": "incomplete",
                    "incomplete_details": {"reason": "max_output_tokens"},
                    "usage": {"output_tokens": 12000},
                },
            )
        return httpx.Response(200, json={"id": "resp-complete", "status": "completed"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await post_openai_response(
            client,
            url="https://api.openai.test/responses",
            headers={"Authorization": "Bearer test"},
            request={"model": "gpt-test", "service_tier": "flex", "max_output_tokens": 12_000},
            logger=logging.getLogger("test"),
            operation="test operation",
            max_output_tokens_retry=24_000,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert [request["max_output_tokens"] for request in requests] == [12_000, 24_000]


@pytest.mark.anyio
async def test_content_filter_incomplete_is_not_retried() -> None:
    request_count = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            json={"id": "resp-filtered", "status": "incomplete", "incomplete_details": {"reason": "content_filter"}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await post_openai_response(
            client,
            url="https://api.openai.test/responses",
            headers={"Authorization": "Bearer test"},
            request={"model": "gpt-test", "service_tier": "flex", "max_output_tokens": 12_000},
            logger=logging.getLogger("test"),
            operation="test operation",
            max_output_tokens_retry=24_000,
        )

    assert response.json()["status"] == "incomplete"
    assert request_count == 1


@pytest.mark.anyio
async def test_unknown_failed_response_retries_once_at_same_budget() -> None:
    requests: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        status = "failed" if len(requests) == 1 else "completed"
        return httpx.Response(200, json={"id": f"resp-{len(requests)}", "status": status})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await post_openai_response(
            client,
            url="https://api.openai.test/responses",
            headers={"Authorization": "Bearer test"},
            request={"model": "gpt-test", "service_tier": "flex", "max_output_tokens": 12_000},
            logger=logging.getLogger("test"),
            operation="test operation",
            max_output_tokens_retry=24_000,
        )

    assert response.json()["status"] == "completed"
    assert [request["max_output_tokens"] for request in requests] == [12_000, 12_000]
