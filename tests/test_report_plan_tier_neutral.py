from intel_mcp.report_plan import REPORT_PLAN_INSTRUCTIONS


def test_report_plan_does_not_hard_code_result_count() -> None:
    assert "Do not hard-code presentation breadth" in REPORT_PLAN_INSTRUCTIONS
    assert "The report tier decides how many results to display" in REPORT_PLAN_INSTRUCTIONS
    assert "top 5, top 10 or top 100" in REPORT_PLAN_INSTRUCTIONS
