from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCallMetrics:
    worker_model: str | None = None
    worker_calls: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0


_current_metrics: ContextVar[ToolCallMetrics | None] = ContextVar("mcp_tool_call_metrics", default=None)


def begin_metrics() -> tuple[ToolCallMetrics, Token[ToolCallMetrics | None]]:
    metrics = ToolCallMetrics()
    return metrics, _current_metrics.set(metrics)


def end_metrics(token: Token[ToolCallMetrics | None]) -> None:
    _current_metrics.reset(token)


def set_worker_model(model: str) -> None:
    metrics = _current_metrics.get()
    if metrics is not None:
        metrics.worker_model = model


def record_worker_response(model: str, payload: dict[str, Any]) -> None:
    metrics = _current_metrics.get()
    if metrics is None:
        return
    metrics.worker_model = model
    metrics.worker_calls += 1
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return

    def count(value: Any) -> int:
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

    input_tokens = count(usage.get("input_tokens"))
    output_tokens = count(usage.get("output_tokens"))
    total_tokens = count(usage.get("total_tokens")) or input_tokens + output_tokens
    input_details = usage.get("input_tokens_details")
    output_details = usage.get("output_tokens_details")
    cached_tokens = count(input_details.get("cached_tokens")) if isinstance(input_details, dict) else 0
    reasoning_tokens = count(output_details.get("reasoning_tokens")) if isinstance(output_details, dict) else 0
    metrics.input_tokens += input_tokens
    metrics.cached_input_tokens += min(input_tokens, cached_tokens)
    metrics.output_tokens += output_tokens
    metrics.reasoning_tokens += min(output_tokens, reasoning_tokens)
    metrics.total_tokens += total_tokens
