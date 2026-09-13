from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


FLEX_429_MAX_ATTEMPTS = 4
FLEX_429_BACKOFF_BASE_SECONDS = 2.0
FLEX_429_BACKOFF_MAX_SECONDS = 60.0

_NON_TRANSIENT_429_CODES = {
    "billing_hard_limit_reached",
    "insufficient_quota",
}


def _error_details(response: httpx.Response) -> tuple[str, str]:
    try:
        body = response.json()
    except ValueError:
        return "", ""
    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return "", ""
    return str(error.get("code") or "").lower(), str(error.get("type") or "").lower()


def _is_transient_flex_429(response: httpx.Response) -> bool:
    if response.status_code != 429:
        return False
    code, error_type = _error_details(response)
    return code not in _NON_TRANSIENT_429_CODES and error_type not in _NON_TRANSIENT_429_CODES


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def _retry_delay(response: httpx.Response, retry_number: int) -> float:
    exponential = FLEX_429_BACKOFF_BASE_SECONDS * (2 ** max(0, retry_number - 1))
    jittered = exponential + random.uniform(0.0, min(1.0, exponential / 4))
    retry_after = _retry_after_seconds(response) or 0.0
    return min(FLEX_429_BACKOFF_MAX_SECONDS, max(jittered, retry_after))


async def post_openai_response(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    request: dict[str, Any],
    logger: logging.Logger,
    operation: str,
) -> httpx.Response:
    """Retry temporary Flex-capacity 429s, then make one automatic-tier attempt."""

    if request.get("service_tier") != "flex":
        return await client.post(url, headers=headers, json=request)

    response: httpx.Response | None = None
    for attempt in range(1, FLEX_429_MAX_ATTEMPTS + 1):
        response = await client.post(url, headers=headers, json=request)
        if not _is_transient_flex_429(response):
            return response
        code, error_type = _error_details(response)
        if attempt == FLEX_429_MAX_ATTEMPTS:
            break
        delay = _retry_delay(response, attempt)
        logger.warning(
            "%s temporary Flex capacity response: status=429 code=%s type=%s "
            "attempt=%s/%s retry_in_seconds=%.2f request_id=%s",
            operation,
            code or "unknown",
            error_type or "unknown",
            attempt,
            FLEX_429_MAX_ATTEMPTS,
            delay,
            response.headers.get("x-request-id") or "unknown",
        )
        await asyncio.sleep(delay)

    fallback_request = dict(request)
    fallback_request["service_tier"] = "auto"
    logger.warning(
        "%s Flex capacity remained unavailable after %s attempts; falling back to auto tier",
        operation,
        FLEX_429_MAX_ATTEMPTS,
    )
    return await client.post(url, headers=headers, json=fallback_request)
