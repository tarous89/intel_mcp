"""Authorization adapter for the deterministic selection tools.

Phase one reuses existing filter/profile permissions. It does not grant a new
entitlement or create an analysis. Every base trial must be admitted: never rank
an allowance-truncated cohort. Exact retries reuse existing unique-ID metering.
"""
from .selection import SelectionError


async def authorized_selection(control, engine, analysis_id, criteria, expected_snapshot=None):
    # Empty filter-access is supported by App and validates subject, lease and tool access.
    await control.authorize_filter_results(analysis_id, [])
    if not hasattr(engine, "selection"):
        raise SelectionError("SELECTION_DATABASE_REQUIRED: Configure the approved database reader.")
    dataset = await engine.selection(criteria)
    if expected_snapshot is not None:
        dataset.check_snapshot(expected_snapshot)
    ids = list(dataset.records)
    for start in range(0, len(ids), 100):
        batch = ids[start:start + 100]
        access = (await control.authorize_filter_results(analysis_id, batch)).access
        if set(access.allowed_trial_ids) != set(batch):
            raise SelectionError("SELECTION_ALLOWANCE_INSUFFICIENT: Full cohort access required; no partial result. Previously admitted IDs remain metered.")
    for start in range(0, len(ids), 10):
        batch = ids[start:start + 10]
        access = (await control.authorize_profiles(analysis_id, batch)).access
        if set(access.allowed_trial_ids) != set(batch):
            raise SelectionError("SELECTION_ALLOWANCE_INSUFFICIENT: Full profile access required; no partial result. Previously admitted IDs remain metered.")
    # Revalidate expiry/ownership after potentially long metering, before releasing any result.
    await control.authorize_filter_results(analysis_id, [])
    return dataset
