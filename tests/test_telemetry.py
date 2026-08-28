from intel_mcp.telemetry import begin_metrics, end_metrics, record_worker_response


def test_worker_usage_aggregates_actual_response_tokens() -> None:
    metrics, token = begin_metrics()
    try:
        record_worker_response(
            "gpt-5.6-luna",
            {
                "usage": {
                    "input_tokens": 1_000,
                    "input_tokens_details": {"cached_tokens": 250},
                    "output_tokens": 300,
                    "output_tokens_details": {"reasoning_tokens": 120},
                    "total_tokens": 1_300,
                }
            },
        )
        record_worker_response(
            "gpt-5.6-luna",
            {"usage": {"input_tokens": 500, "output_tokens": 100, "total_tokens": 600}},
        )
    finally:
        end_metrics(token)

    assert metrics.worker_model == "gpt-5.6-luna"
    assert metrics.worker_calls == 2
    assert metrics.input_tokens == 1_500
    assert metrics.cached_input_tokens == 250
    assert metrics.output_tokens == 400
    assert metrics.reasoning_tokens == 120
    assert metrics.total_tokens == 1_900
