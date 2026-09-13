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
