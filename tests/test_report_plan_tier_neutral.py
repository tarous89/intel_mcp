from intel_mcp.report_plan import REPORT_PLAN_INSTRUCTIONS


def test_report_plan_is_tier_neutral_about_result_count() -> None:
    assert "Describe the analysis itself, not the display limit" in REPORT_PLAN_INSTRUCTIONS
    assert "the report tier/executor decides how many results to display" in REPORT_PLAN_INSTRUCTIONS
    assert "top 3/top 5 rankings" not in REPORT_PLAN_INSTRUCTIONS
    assert "top 5/top 10" not in REPORT_PLAN_INSTRUCTIONS
