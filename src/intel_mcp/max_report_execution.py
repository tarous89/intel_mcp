from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import replace
from typing import Any

import httpx

from intel_mcp.config import Settings
from intel_mcp.control_plane import ControlPlaneClient, ControlPlaneError
from intel_mcp.engine import EngineClient, EngineError
from intel_mcp.engine_database import DatabaseEngineClient
from intel_mcp.extraction import ExtractionVariable, ExtractorError, TerraExtractor, extraction_key
from intel_mcp.light_report_execution import ReportExecutionControl, ReportExecutionError
from intel_mcp.max_candidate_screening import (
    CANDIDATE_POOL_TARGET,
    MAX_CANDIDATE_POOL,
    MAX_CANDIDATE_SCREEN_BATCH,
    MAX_CANDIDATE_SCREEN_CONCURRENCY,
    CandidateAssessment,
    CandidateFilter,
    CandidateFilterPlan,
    candidate_screening_key,
    screening_summary,
    select_screened_candidates,
)
from intel_mcp.max_report import (
    MAX_NONDETERMINISTIC_VARIABLES,
    MAX_REPORT_MODEL,
    MAX_REPORT_SERVICE_TIER,
    MAX_REPORT_TRIAL_COUNT,
    AnalysisSpecification,
    MaxAnalysisPlan,
    MaxObjectiveResult,
    MaxReportError,
    TerraMaxReportRunner,
    build_field_catalog,
    fit_complete_profile_sample,
    max_group_variables,
    resolve_profile_path,
)
from intel_mcp.models import TrialFilters, TrialSort
from intel_mcp.profiles import (
    FullProfileItem,
    MAX_PROFILES_PER_CALL,
    project_profile,
)


LOGGER = logging.getLogger("intel_mcp")
# Ten concurrent Flex workers keep the worst-case 100-profile enrichment phase
# inside the six-hour Max lease without creating an unbounded fan-out.
MAX_EXTRACTION_CONCURRENCY = 10
MAX_PROFILE_LOAD_CONCURRENCY = 5
CANDIDATE_PROFILE_SECTIONS = ["overview", "population", "trial_design", "interventions"]


def _execution_plan(plan: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if plan.get("version") != 4:
        raise MaxReportError(
            "MAX_REPORT_PLAN_VERSION_REQUIRED",
            "Max execution requires a current v4 report plan. Please regenerate the plan.",
            False,
        )
    cohorts = plan.get("studyCohorts")
    sections = plan.get("reportSections")
    if not isinstance(cohorts, list) or not 3 <= len(cohorts) <= 5:
        raise MaxReportError("MAX_REPORT_PLAN_INVALID", "The approved Max trial groups are invalid.", False)
    if not isinstance(sections, list) or not 1 <= len(sections) <= 7:
        raise MaxReportError("MAX_REPORT_PLAN_INVALID", "The approved Max analyses are invalid.", False)
    for index, cohort in enumerate(cohorts):
        if not isinstance(cohort, dict):
            raise MaxReportError("MAX_REPORT_PLAN_INVALID", "A Max trial group is invalid.", False)
        discovery = cohort.get("discoveryFilter")
        segments = cohort.get("selectionSegments")
        if not isinstance(discovery, dict) or not isinstance(segments, list) or not segments:
            raise MaxReportError(
                "MAX_REPORT_PLAN_METADATA_REQUIRED",
                "This approved plan predates executable Max group labels. Please regenerate the plan.",
                False,
            )
        if index == 0 and len(segments) != 1:
            raise MaxReportError("MAX_REPORT_PLAN_INVALID", "The shared trial group is invalid.", False)
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get("sharedAnalysis"), dict) or not isinstance(section.get("maxAnalysis"), dict):
            raise MaxReportError("MAX_REPORT_PLAN_INVALID", "A Max analysis pair is invalid.", False)
    return cohorts, sections


def _trial_filters(discovery: dict[str, Any]) -> TrialFilters:
    field = discovery.get("field")
    values = discovery.get("values")
    if field not in {"diseases", "therapeutic_areas", "phase", "modalities", "country_codes"}:
        raise MaxReportError("MAX_REPORT_PLAN_INVALID", "A Max discovery filter is unsupported.", False)
    if not isinstance(values, list) or not values or any(not isinstance(value, str) for value in values):
        raise MaxReportError("MAX_REPORT_PLAN_INVALID", "A Max discovery filter has invalid values.", False)
    if field == "phase":
        try:
            phase_values = [int(value) for value in values]
        except ValueError as error:
            raise MaxReportError("MAX_REPORT_PLAN_INVALID", "A Max phase discovery filter is invalid.", False) from error
        payload = {field: {"operator": "contains_any", "values": phase_values}}
    else:
        payload = {field: {"operator": "contains_any", "values": values}}
    try:
        return TrialFilters.model_validate(payload)
    except ValueError as error:
        raise MaxReportError("MAX_REPORT_PLAN_INVALID", "A Max discovery filter is invalid.", False) from error


def _candidate_trial_filters(candidate: CandidateFilter) -> TrialFilters:
    payload: dict[str, Any] = {}
    if candidate.therapeutic_areas:
        payload["therapeutic_areas"] = {
            "operator": "contains_any",
            "values": candidate.therapeutic_areas,
        }
    if candidate.phase:
        payload["phase"] = {"operator": "contains_any", "values": candidate.phase}
    if candidate.modalities:
        payload["modalities"] = {
            "operator": "contains_any",
            "values": candidate.modalities,
        }
    if candidate.country_codes:
        payload["country_codes"] = {
            "operator": "contains_any",
            "values": candidate.country_codes,
        }
    try:
        return TrialFilters.model_validate(payload)
    except ValueError as error:
        raise MaxReportError(
            "MAX_REPORT_CANDIDATE_PLAN_INVALID",
            "The candidate-search plan contains an invalid deterministic filter.",
            True,
        ) from error


def _candidate_pool_limit(limits: Any) -> int:
    values = [
        int(getattr(limits, "filtered_trial_ids", 0) or 0),
        int(getattr(limits, "profiles", 0) or 0),
        int(getattr(limits, "classified_trials", 0) or 0),
    ]
    return min(CANDIDATE_POOL_TARGET, MAX_CANDIDATE_POOL, *values)


def _discovery_quotas(cohort_count: int) -> list[int]:
    adjacent_count = cohort_count - 1
    primary = max(40, MAX_REPORT_TRIAL_COUNT - 15 * adjacent_count)
    remaining = MAX_REPORT_TRIAL_COUNT - primary
    base, extra = divmod(remaining, adjacent_count)
    return [primary, *[base + (1 if index < extra else 0) for index in range(adjacent_count)]]


def _steps(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"key": "trial_selection", "label": "Building the Max evidence cohort", "status": "waiting"},
        {"key": "analysis_plan", "label": "Preparing the analysis specification", "status": "waiting"},
        {"key": "dataset_population", "label": "Populating the profile dataset", "status": "waiting"},
        *[
            {
                "key": f"objective_{index + 1}",
                "label": f"Analyzing {str(section.get('maxAnalysis', {}).get('title') or section.get('title') or 'report area')}",
                "status": "waiting",
            }
            for index, section in enumerate(sections)
        ],
        {"key": "final_report", "label": "Preparing the final Max Report", "status": "waiting"},
    ]


def _mark(
    progress: dict[str, Any],
    key: str,
    status: str,
    *,
    completed_units: int | None = None,
    total_units: int | None = None,
) -> dict[str, Any]:
    next_progress = {
        **progress,
        "steps": [dict(step) for step in progress.get("steps", []) if isinstance(step, dict)],
    }
    for step in next_progress["steps"]:
        if step.get("key") != key:
            continue
        step["status"] = status
        if completed_units is not None:
            step["completedUnits"] = completed_units
        if total_units is not None:
            step["totalUnits"] = total_units
        break
    next_progress["completedSteps"] = sum(
        1 for step in next_progress["steps"] if step.get("status") == "completed"
    )
    next_progress["totalSteps"] = len(next_progress["steps"])
    next_progress["stage"] = key
    return next_progress


def _stratified_sample(
    report_run_id: str,
    profiles: list[FullProfileItem],
    discovery_indices: dict[str, set[int]],
    maximum: int = 10,
) -> list[FullProfileItem]:
    profiles_by_id = {item.eu_number: item for item in profiles}

    def rank(trial_id: str) -> str:
        return hashlib.sha256(f"{report_run_id}:{trial_id}".encode("utf-8")).hexdigest()

    selected: list[str] = []
    cohort_indices = sorted({index for values in discovery_indices.values() for index in values})
    for cohort_index in cohort_indices:
        candidates = sorted(
            (
                trial_id
                for trial_id, indices in discovery_indices.items()
                if cohort_index in indices and trial_id not in selected
            ),
            key=rank,
        )
        if candidates:
            selected.append(candidates[0])
        if len(selected) >= maximum:
            break
    for trial_id in sorted(profiles_by_id, key=rank):
        if trial_id not in selected:
            selected.append(trial_id)
        if len(selected) >= maximum:
            break
    return [profiles_by_id[trial_id] for trial_id in selected]


def _definitions(
    analysis_plan: MaxAnalysisPlan,
    group_variables: list[ExtractionVariable],
    segment_metadata: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    definitions: dict[str, dict[str, Any]] = {}
    for variable in analysis_plan.direct_variables:
        definitions[variable.name] = {
            "label": variable.label,
            "description": variable.description,
            "kind": variable.kind,
            "source": "deterministic_profile_path",
            "profile_path": variable.profile_path,
            "analysis_indices": variable.analysis_indices,
        }
    metadata_by_name = {
        item["variable_name"]: item
        for item in segment_metadata
        if item.get("variable_name")
    }
    for variable in group_variables:
        metadata = metadata_by_name[variable.name]
        definitions[variable.name] = {
            "label": metadata["label"],
            "description": "Semantic Trial Profile classification for a planned Max segment.",
            "kind": "boolean",
            "source": "profile_extraction",
            "analysis_indices": list(range(len(analysis_plan.analyses))),
        }
    for variable in analysis_plan.semantic_variables:
        definitions[variable.name] = {
            "label": variable.label,
            "description": variable.instruction,
            "kind": variable.kind,
            "source": "profile_extraction",
            "analysis_indices": variable.analysis_indices,
        }
    return definitions


def _analysis_specification(plan: MaxAnalysisPlan, index: int) -> AnalysisSpecification:
    return next(item for item in plan.analyses if item.analysis_index == index)


def _primary_segment_metadata(cohorts: list[dict[str, Any]]) -> dict[str, Any]:
    cohort = cohorts[0]
    raw = cohort["selectionSegments"][0]
    key = str(raw.get("key") or "").strip()
    label = str(raw.get("label") or "").strip()
    inclusion = [
        str(value).strip()
        for value in raw.get("inclusionCriteria") or []
        if str(value).strip()
    ]
    exclusion = [
        str(value).strip()
        for value in raw.get("exclusionCriteria") or []
        if str(value).strip()
    ]
    if not key or not label or not inclusion:
        raise MaxReportError(
            "MAX_REPORT_PLAN_INVALID",
            "The shared Max trial group is invalid.",
            False,
        )
    return {
        "key": key,
        "label": label,
        "cohort_index": 0,
        "cohort_title": str(cohort.get("title") or label),
        "inclusion_criteria": inclusion,
        "exclusion_criteria": exclusion,
        "membership_source": "deterministic_discovery",
    }


class MaxReportExecutor:
    def __init__(
        self,
        settings: Settings,
        *,
        openai_transport: httpx.AsyncBaseTransport | None = None,
        control_transport: httpx.AsyncBaseTransport | None = None,
        engine_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._runner = TerraMaxReportRunner(settings, transport=openai_transport)
        self._control = ReportExecutionControl(settings, transport=control_transport)
        self._analysis_control = ControlPlaneClient(settings, transport=control_transport)
        self._engine: EngineClient | DatabaseEngineClient = (
            DatabaseEngineClient(settings)
            if settings.engine_source == "database"
            else EngineClient(settings, transport=engine_transport)
        )
        extraction_settings = replace(
            settings,
            extractor_model=MAX_REPORT_MODEL,
            extractor_reasoning_effort="high",
            extractor_service_tier=MAX_REPORT_SERVICE_TIER,
            extractor_timeout_seconds=max(settings.extractor_timeout_seconds, 900),
        )
        self._extractor = TerraExtractor(extraction_settings, transport=openai_transport)

    async def _discover(
        self,
        analysis_id: str,
        cohorts: list[dict[str, Any]],
    ) -> tuple[list[str], dict[str, set[int]]]:
        quotas = _discovery_quotas(len(cohorts))
        filters = [_trial_filters(cohort["discoveryFilter"]) for cohort in cohorts]
        selected: list[str] = []
        discovery_indices: dict[str, set[int]] = {}
        offsets = [0 for _ in cohorts]
        exhausted = [False for _ in cohorts]

        async def read(index: int, limit: int) -> None:
            if limit <= 0 or exhausted[index]:
                return
            try:
                result = await self._engine.filter_trials(
                    filters=filters[index],
                    sort=TrialSort(),
                    limit=min(100, limit),
                    offset=offsets[index],
                )
                ids = [item.eu_number for item in result.data]
                access = await self._analysis_control.authorize_filter_results(analysis_id, ids)
            except ControlPlaneError as error:
                raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
            except EngineError as error:
                raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
            offsets[index] += len(result.data)
            exhausted[index] = len(result.data) < limit
            allowed = set(access.access.allowed_trial_ids)
            for trial_id in ids:
                if trial_id not in allowed:
                    continue
                if trial_id in selected:
                    discovery_indices.setdefault(trial_id, set()).add(index)
                elif len(selected) < MAX_REPORT_TRIAL_COUNT:
                    selected.append(trial_id)
                    discovery_indices.setdefault(trial_id, set()).add(index)

        for index, quota in enumerate(quotas):
            await read(index, quota)

        # Reallocate unused/overlapping quota in small deterministic rounds. This
        # preserves broad representation without ever authorizing >100 unique IDs.
        rounds = 0
        while len(selected) < MAX_REPORT_TRIAL_COUNT and not all(exhausted) and rounds < 4:
            before = len(selected)
            for index in range(len(cohorts)):
                remaining = MAX_REPORT_TRIAL_COUNT - len(selected)
                if remaining <= 0:
                    break
                await read(index, min(25, remaining))
            if len(selected) == before:
                break
            rounds += 1

        if not selected:
            raise MaxReportError(
                "MAX_REPORT_NO_TRIALS",
                "No approved Trial Profiles matched the planned Max evidence groups.",
                False,
            )
        return selected, discovery_indices

    async def _discover_candidates(
        self,
        analysis_id: str,
        cohorts: list[dict[str, Any]],
        filter_plan: CandidateFilterPlan,
        candidate_limit: int,
    ) -> tuple[list[str], dict[str, set[int]]]:
        queries: list[dict[str, Any]] = []
        query_by_key: dict[str, dict[str, Any]] = {}

        def add_query(filters: TrialFilters, cohort_index: int | None) -> None:
            key = json.dumps(
                filters.model_dump(mode="json", exclude_none=True),
                sort_keys=True,
                separators=(",", ":"),
            )
            existing = query_by_key.get(key)
            if existing is not None:
                if cohort_index is not None:
                    existing["cohort_indices"].add(cohort_index)
                return
            query = {
                "filters": filters,
                "cohort_indices": {cohort_index} if cohort_index is not None else set(),
                "offset": 0,
                "exhausted": False,
            }
            query_by_key[key] = query
            queries.append(query)

        # Preserve the approved plan's exact discovery seeds, including disease
        # names, before adding the broader reliable-field progression.
        for cohort_index, cohort in enumerate(cohorts):
            add_query(_trial_filters(cohort["discoveryFilter"]), cohort_index)
        for candidate in filter_plan.filters:
            add_query(_candidate_trial_filters(candidate), None)

        selected: list[str] = []
        selected_ids: set[str] = set()
        discovery_indices: dict[str, set[int]] = {}
        access_exhausted = False

        while len(selected) < candidate_limit and not access_exhausted:
            active = [query for query in queries if not query["exhausted"]]
            if not active:
                break
            before = len(selected)
            for query in active:
                remaining = candidate_limit - len(selected)
                if remaining <= 0:
                    break
                page_size = min(100, remaining)
                try:
                    result = await self._engine.filter_trials(
                        filters=query["filters"],
                        sort=TrialSort(),
                        limit=page_size,
                        offset=query["offset"],
                    )
                    ids = [item.eu_number for item in result.data]
                    access = await self._analysis_control.authorize_filter_results(analysis_id, ids)
                except ControlPlaneError as error:
                    raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
                except EngineError as error:
                    raise MaxReportError(error.code, error.message, error.status_code >= 500) from error

                query["offset"] += len(result.data)
                query["exhausted"] = (
                    query["offset"] >= result.counts.total_matches
                    or len(result.data) < page_size
                )
                allowed = set(access.access.allowed_trial_ids)
                for trial_id in ids:
                    if trial_id not in allowed:
                        continue
                    if query["cohort_indices"]:
                        discovery_indices.setdefault(trial_id, set()).update(query["cohort_indices"])
                    if trial_id not in selected_ids and len(selected) < candidate_limit:
                        selected.append(trial_id)
                        selected_ids.add(trial_id)
                access_exhausted = bool(access.access.exhausted) and len(selected) < candidate_limit
                if access_exhausted:
                    break
            if len(selected) == before and all(query["exhausted"] for query in queries):
                break

        if not selected:
            raise MaxReportError(
                "MAX_REPORT_NO_TRIALS",
                "No approved Trial Profiles matched the planned Max evidence groups.",
                False,
            )
        return selected, discovery_indices

    async def _load_compact_profiles(
        self,
        analysis_id: str,
        trial_ids: list[str],
    ) -> list[dict[str, Any]]:
        semaphore = asyncio.Semaphore(MAX_PROFILE_LOAD_CONCURRENCY)

        async def load(index: int, batch: list[str]) -> tuple[int, list[dict[str, Any]]]:
            async with semaphore:
                try:
                    result = await self._engine.get_profiles(batch)
                    access = await self._analysis_control.authorize_profiles(
                        analysis_id,
                        [item.eu_number for item in result.data],
                    )
                except ControlPlaneError as error:
                    raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
                except EngineError as error:
                    raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
                returned = [item.eu_number for item in result.data]
                if result.unavailable_trial_ids or returned != batch or access.access.allowed_trial_ids != batch:
                    raise MaxReportError(
                        "MAX_REPORT_PROFILE_ACCESS_INCOMPLETE",
                        "One or more candidate Trial Profiles could not be loaded.",
                        True,
                    )
                return index, [
                    {
                        "trial_id": item.eu_number,
                        "profile": project_profile(item.profile, CANDIDATE_PROFILE_SECTIONS),
                    }
                    for item in result.data
                ]

        tasks = [
            load(index, trial_ids[start : start + MAX_PROFILES_PER_CALL])
            for index, start in enumerate(range(0, len(trial_ids), MAX_PROFILES_PER_CALL))
        ]
        batches = sorted(await asyncio.gather(*tasks), key=lambda item: item[0])
        return [profile for _, batch in batches for profile in batch]

    async def _screen_candidates(
        self,
        *,
        analysis_id: str,
        context: str,
        insights: str,
        approved_plan: dict[str, Any],
        segment_metadata: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
    ) -> list[CandidateAssessment]:
        stable_segments = [
            {
                "key": item["key"],
                "label": item["label"],
                "cohort_index": item["cohort_index"],
                "cohort_title": item["cohort_title"],
                "inclusion_criteria": item["inclusion_criteria"],
                "exclusion_criteria": item["exclusion_criteria"],
            }
            for item in segment_metadata
        ]
        semaphore = asyncio.Semaphore(MAX_CANDIDATE_SCREEN_CONCURRENCY)

        async def screen(batch: list[dict[str, Any]]) -> list[CandidateAssessment]:
            async with semaphore:
                keys = [
                    candidate_screening_key(str(item["trial_id"]), stable_segments)
                    for item in batch
                ]
                try:
                    reservation = await self._analysis_control.authorize_classifications(
                        analysis_id,
                        keys,
                        "reserve",
                    )
                except ControlPlaneError as error:
                    raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
                if reservation.access.allowed_classification_keys != keys:
                    allowed_keys = reservation.access.allowed_classification_keys
                    if allowed_keys:
                        try:
                            await self._analysis_control.authorize_classifications(
                                analysis_id,
                                allowed_keys,
                                "release",
                            )
                        except ControlPlaneError:
                            pass
                    raise MaxReportError(
                        "MAX_REPORT_SCREEN_ACCESS_INCOMPLETE",
                        "The candidate screening allowance was incomplete.",
                        True,
                    )
                try:
                    assessments = await self._runner.screen_candidate_batch(
                        context=context,
                        insights=insights,
                        approved_plan=approved_plan,
                        segment_metadata=stable_segments,
                        candidates=batch,
                    )
                except MaxReportError:
                    try:
                        await self._analysis_control.authorize_classifications(
                            analysis_id,
                            keys,
                            "release",
                        )
                    except ControlPlaneError:
                        pass
                    raise
                try:
                    await self._analysis_control.authorize_classifications(
                        analysis_id,
                        keys,
                        "commit",
                    )
                except ControlPlaneError as error:
                    try:
                        await self._analysis_control.authorize_classifications(
                            analysis_id,
                            keys,
                            "release",
                        )
                    except ControlPlaneError:
                        pass
                    raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
                return assessments

        batches = [
            candidates[start : start + MAX_CANDIDATE_SCREEN_BATCH]
            for start in range(0, len(candidates), MAX_CANDIDATE_SCREEN_BATCH)
        ]
        tasks = [asyncio.create_task(screen(batch)) for batch in batches]
        try:
            results = await asyncio.gather(*tasks)
        except Exception:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        return [assessment for batch in results for assessment in batch]

    async def _load_profiles(self, analysis_id: str, trial_ids: list[str]) -> list[FullProfileItem]:
        profiles: list[FullProfileItem] = []
        for start in range(0, len(trial_ids), MAX_PROFILES_PER_CALL):
            batch = trial_ids[start : start + MAX_PROFILES_PER_CALL]
            try:
                result = await self._engine.get_profiles(batch)
                access = await self._analysis_control.authorize_profiles(
                    analysis_id,
                    [item.eu_number for item in result.data],
                )
            except ControlPlaneError as error:
                raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
            except EngineError as error:
                raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
            returned = [item.eu_number for item in result.data]
            if result.unavailable_trial_ids or returned != batch or access.access.allowed_trial_ids != batch:
                raise MaxReportError(
                    "MAX_REPORT_PROFILE_ACCESS_INCOMPLETE",
                    "One or more selected Trial Profiles could not be loaded.",
                    True,
                )
            profiles.extend(result.data)
        return profiles

    async def _extract_profile_variables(
        self,
        analysis_id: str,
        profile: FullProfileItem,
        variables: list[ExtractionVariable],
    ) -> dict[str, Any]:
        key = extraction_key(profile.eu_number, variables)
        try:
            reservation = await self._analysis_control.authorize_extraction(
                analysis_id,
                key,
                len(variables),
                "reserve",
            )
        except ControlPlaneError as error:
            raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
        try:
            values = await self._extractor.extract(
                trial_id=profile.eu_number,
                profile=profile.profile,
                variables=variables,
                model=MAX_REPORT_MODEL,
            )
        except ExtractorError as error:
            try:
                await self._analysis_control.authorize_extraction(
                    analysis_id, key, len(variables), "release"
                )
            except ControlPlaneError:
                pass
            raise MaxReportError(error.code, error.message, error.retryable) from error
        try:
            await self._analysis_control.authorize_extraction(
                analysis_id,
                reservation.access.extraction_key,
                len(variables),
                "commit",
            )
        except ControlPlaneError as error:
            raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
        return values

    async def _populate_dataset(
        self,
        *,
        report_run_id: str,
        analysis_id: str,
        profiles: list[FullProfileItem],
        discovery_indices: dict[str, set[int]],
        analysis_plan: MaxAnalysisPlan,
        group_variables: list[ExtractionVariable],
        segment_metadata: list[dict[str, Any]],
        primary_segment_key: str | None,
        progress: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        semantic_variables = [
            *group_variables,
            *[
                ExtractionVariable(
                    name=item.name,
                    instruction=item.instruction,
                    value_type=item.value_type,
                )
                for item in analysis_plan.semantic_variables
            ],
        ]
        if len(semantic_variables) > MAX_NONDETERMINISTIC_VARIABLES:
            raise MaxReportError("MAX_REPORT_VARIABLE_BUDGET_INVALID", "The extraction plan exceeds 20 variables.", False)
        rows: list[dict[str, Any]] = []
        segment_by_variable = {
            item["variable_name"]: item["key"]
            for item in segment_metadata
            if item.get("variable_name")
        }

        for start in range(0, len(profiles), MAX_EXTRACTION_CONCURRENCY):
            batch = profiles[start : start + MAX_EXTRACTION_CONCURRENCY]
            extracted = await asyncio.gather(
                *[
                    self._extract_profile_variables(analysis_id, profile, semantic_variables)
                    for profile in batch
                ]
            )
            for profile, semantic_values in zip(batch, extracted, strict=True):
                direct_values = {
                    variable.name: resolve_profile_path(
                        profile.profile,
                        variable.profile_path,
                        profile.eu_number,
                    )
                    for variable in analysis_plan.direct_variables
                }
                segment_keys = (
                    [primary_segment_key]
                    if primary_segment_key is not None
                    and 0 in discovery_indices.get(profile.eu_number, set())
                    else []
                ) + [
                    segment_by_variable[name]
                    for name, value in semantic_values.items()
                    if name in segment_by_variable and value is True
                ]
                uncertain_segment_keys = [
                    segment_by_variable[name]
                    for name, value in semantic_values.items()
                    if name in segment_by_variable and value is None
                ]
                rows.append(
                    {
                        "trial_id": profile.eu_number,
                        "discovery_cohort_indices": sorted(discovery_indices.get(profile.eu_number, set())),
                        "segment_keys": segment_keys,
                        "uncertain_segment_keys": uncertain_segment_keys,
                        "values": {**direct_values, **semantic_values},
                    }
                )
            completed = min(len(profiles), start + len(batch))
            progress = _mark(
                progress,
                "dataset_population",
                "in_progress",
                completed_units=completed,
                total_units=len(profiles),
            )
            await self._control.progress(report_run_id, progress)
        return rows, progress

    @staticmethod
    def _cohort_summary(
        rows: list[dict[str, Any]],
        segment_metadata: list[dict[str, Any]],
    ) -> dict[str, Any]:
        summary = []
        for segment in segment_metadata:
            summary.append(
                {
                    "title": (
                        segment.get("cohort_title")
                        if segment.get("cohort_index") == 0
                        else segment["label"]
                    ),
                    "role": "primary" if segment.get("cohort_index") == 0 else "adjacent",
                    "trialCount": sum(
                        1 for row in rows if segment["key"] in row.get("segment_keys", [])
                    ),
                }
            )
        return {"totalTrials": len(rows), "cohorts": summary, "overlapping": True}

    async def execute(self, report_run_id: str) -> None:
        progress: dict[str, Any] = {
            "version": 2,
            "stage": "starting",
            "completedSteps": 0,
            "totalSteps": 0,
            "steps": [],
        }
        try:
            job = await self._control.load(report_run_id)
            if job.get("status") != "queued":
                LOGGER.info("Ignoring non-queued Max report run: report_run_id=%s status=%s", report_run_id, job.get("status"))
                return
            if job.get("tier") != "max":
                raise MaxReportError("MAX_REPORT_TIER_REQUIRED", "This executor supports Max reports only.", False)
            context = job.get("context")
            insights = job.get("insights")
            approved_plan = job.get("plan")
            if not isinstance(context, str) or not isinstance(insights, str) or not isinstance(approved_plan, dict):
                raise MaxReportError("MAX_REPORT_JOB_INVALID", "The Max report job is incomplete.", False)
            cohorts, sections = _execution_plan(approved_plan)
            progress = {
                "version": 2,
                "stage": "starting",
                "completedSteps": 0,
                "totalSteps": len(sections) + 4,
                "steps": _steps(sections),
                "selectedTrials": [],
                "sectionsCompleted": 0,
            }
            await self._control.progress(report_run_id, progress)

            try:
                access = await self._analysis_control.start_analysis(report_run_id)
            except ControlPlaneError as error:
                raise MaxReportError(error.code, error.message, error.status_code >= 500) from error
            analysis_id = access.analysis.analysis_id
            candidate_limit = _candidate_pool_limit(getattr(access.analysis, "limits", None))

            progress = _mark(
                progress,
                "trial_selection",
                "in_progress",
                completed_units=0,
                total_units=(
                    candidate_limit
                    if candidate_limit > MAX_REPORT_TRIAL_COUNT
                    else MAX_REPORT_TRIAL_COUNT
                ),
            )
            await self._control.progress(report_run_id, progress)

            candidate_execution = False
            candidate_overview: dict[str, Any] | None = None
            selected_assessments: dict[str, CandidateAssessment] = {}
            trial_ids: list[str]
            discovery_indices: dict[str, set[int]]
            profiles: list[FullProfileItem]
            group_variables: list[ExtractionVariable]
            segment_metadata: list[dict[str, Any]]
            primary_segment_key: str | None

            if candidate_limit > MAX_REPORT_TRIAL_COUNT:
                try:
                    filter_plan = await self._runner.build_candidate_filter_plan(
                        context=context,
                        insights=insights,
                        approved_plan=approved_plan,
                    )
                    candidate_ids, candidate_discovery_indices = await self._discover_candidates(
                        analysis_id,
                        cohorts,
                        filter_plan,
                        candidate_limit,
                    )
                    candidate_profiles = await self._load_compact_profiles(
                        analysis_id,
                        candidate_ids,
                    )
                    candidate_group_variables, candidate_segment_metadata = max_group_variables(
                        approved_plan,
                        include_primary=True,
                    )
                    progress = _mark(
                        progress,
                        "trial_selection",
                        "in_progress",
                        completed_units=0,
                        total_units=len(candidate_profiles),
                    )
                    await self._control.progress(report_run_id, progress)
                    assessments = await self._screen_candidates(
                        analysis_id=analysis_id,
                        context=context,
                        insights=insights,
                        approved_plan=approved_plan,
                        segment_metadata=candidate_segment_metadata,
                        candidates=candidate_profiles,
                    )
                except MaxReportError as error:
                    LOGGER.warning(
                        "Max candidate screening failed before final cohort selection: report_run_id=%s code=%s",
                        report_run_id,
                        error.code,
                    )
                    raise
                else:
                    segment_cohort_indices = {
                        item["key"]: item["cohort_index"]
                        for item in candidate_segment_metadata
                    }
                    selected = select_screened_candidates(
                        assessments,
                        segment_cohort_indices=segment_cohort_indices,
                        maximum=MAX_REPORT_TRIAL_COUNT,
                    )
                    if not selected:
                        raise MaxReportError(
                            "MAX_REPORT_NO_RELEVANT_TRIALS",
                            "No approved Trial Profiles were sufficiently relevant to the approved report plan.",
                            False,
                        )
                    trial_ids = [item.trial_id for item in selected]
                    selected_assessments = {item.trial_id: item for item in selected}
                    discovery_indices = {
                        trial_id: set(candidate_discovery_indices.get(trial_id, set()))
                        for trial_id in trial_ids
                    }
                    for item in selected:
                        discovery_indices[item.trial_id].update(
                            segment_cohort_indices[key]
                            for key in [*item.segment_keys, *item.uncertain_segment_keys]
                            if key in segment_cohort_indices
                        )
                    profiles = await self._load_profiles(analysis_id, trial_ids)
                    group_variables = candidate_group_variables
                    segment_metadata = candidate_segment_metadata
                    primary_segment_key = None
                    candidate_overview = screening_summary(assessments, selected)
                    candidate_execution = True

            if not candidate_execution:
                group_variables, extracted_segment_metadata = max_group_variables(approved_plan)
                segment_metadata = [
                    _primary_segment_metadata(cohorts),
                    *extracted_segment_metadata,
                ]
                primary_segment_key = segment_metadata[0]["key"]
                trial_ids, discovery_indices = await self._discover(analysis_id, cohorts)
                profiles = await self._load_profiles(analysis_id, trial_ids)

            progress["selectedTrials"] = [
                {
                    "trial_id": trial_id,
                    "group": (
                        "priority"
                        if (
                            selected_assessments[trial_id].tier in {"exact", "close"}
                            if trial_id in selected_assessments
                            else 0 in discovery_indices.get(trial_id, set())
                        )
                        else "adjacent"
                    ),
                    "cohort_index": min(discovery_indices.get(trial_id, {0})),
                }
                for trial_id in trial_ids
            ]
            if candidate_overview is not None:
                progress["candidateScreening"] = candidate_overview
            progress = _mark(
                progress,
                "trial_selection",
                "completed",
                completed_units=(
                    candidate_overview["screenedCandidates"]
                    if candidate_overview is not None
                    else len(profiles)
                ),
                total_units=(
                    candidate_overview["screenedCandidates"]
                    if candidate_overview is not None
                    else len(profiles)
                ),
            )
            await self._control.progress(report_run_id, progress)

            progress = _mark(progress, "analysis_plan", "in_progress")
            await self._control.progress(report_run_id, progress)
            initial_sample = _stratified_sample(report_run_id, profiles, discovery_indices)
            sample = fit_complete_profile_sample(
                context=context,
                insights=insights,
                plan=approved_plan,
                profiles=initial_sample,
            )
            # Catalogue all selected profiles so sparse structured fields such as
            # site investigators remain available even when absent from the ten
            # complete examples sent to the SAP request.
            field_catalog = build_field_catalog(profiles)
            analysis_plan = await self._runner.build_analysis_plan(
                context=context,
                insights=insights,
                approved_plan=approved_plan,
                sample_profiles=sample,
                field_catalog=field_catalog,
                group_variables=group_variables,
                segment_metadata=segment_metadata,
            )
            progress = _mark(progress, "analysis_plan", "completed")
            await self._control.progress(report_run_id, progress)

            progress = _mark(
                progress,
                "dataset_population",
                "in_progress",
                completed_units=0,
                total_units=len(profiles),
            )
            await self._control.progress(report_run_id, progress)
            rows, progress = await self._populate_dataset(
                report_run_id=report_run_id,
                analysis_id=analysis_id,
                profiles=profiles,
                discovery_indices=discovery_indices,
                analysis_plan=analysis_plan,
                group_variables=group_variables,
                segment_metadata=segment_metadata,
                primary_segment_key=primary_segment_key,
                progress=progress,
            )
            progress = _mark(
                progress,
                "dataset_population",
                "completed",
                completed_units=len(rows),
                total_units=len(rows),
            )
            await self._control.progress(report_run_id, progress)

            definitions = _definitions(analysis_plan, group_variables, segment_metadata)
            for index in range(len(sections)):
                progress = _mark(progress, f"objective_{index + 1}", "in_progress")
            await self._control.progress(report_run_id, progress)

            async def analyze(index: int, pair: dict[str, Any]) -> tuple[int, MaxObjectiveResult]:
                return index, await self._runner.analyze_objective(
                    context=context,
                    pair=pair,
                    specification=_analysis_specification(analysis_plan, index),
                    rows=rows,
                    definitions=definitions,
                    segment_metadata=segment_metadata,
                )

            tasks = [
                asyncio.create_task(analyze(index, pair))
                for index, pair in enumerate(sections)
            ]
            results_by_index: list[MaxObjectiveResult | None] = [None] * len(sections)
            try:
                for completed in asyncio.as_completed(tasks):
                    index, result = await completed
                    results_by_index[index] = result
                    available_results = [item for item in results_by_index if item is not None]
                    progress["sectionsCompleted"] = len(available_results)
                    progress["sections"] = [
                        item.model_dump(mode="json") for item in available_results
                    ]
                    progress = _mark(progress, f"objective_{index + 1}", "completed")
                    await self._control.progress(report_run_id, progress)
            except Exception:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
            results = [item for item in results_by_index if item is not None]
            if len(results) != len(sections):
                raise MaxReportError(
                    "MAX_REPORT_OBJECTIVES_INCOMPLETE",
                    "One or more Max report analyses did not complete.",
                    True,
                )

            analyzed_cohort = self._cohort_summary(rows, segment_metadata)
            if candidate_overview is not None:
                analyzed_cohort.update(candidate_overview)
            progress = _mark(progress, "final_report", "in_progress")
            await self._control.progress(report_run_id, progress)
            synthesis = await self._runner.synthesize(
                context=context,
                analyzed_cohort=analyzed_cohort,
                sections=results,
            )
            progress = _mark(progress, "final_report", "completed")
            progress["stage"] = "completed"
            final_report = {
                "version": 2,
                "tier": "max",
                "title": synthesis.title,
                "executiveSummary": synthesis.executive_summary,
                "analyzedCohort": analyzed_cohort,
                "closingNote": synthesis.closing_note,
                "sections": [item.model_dump(mode="json") for item in results],
            }
            await self._control.complete(report_run_id, progress, final_report)
        except (MaxReportError, ReportExecutionError) as error:
            LOGGER.exception("Max report failed: report_run_id=%s code=%s", report_run_id, error.code)
            progress["stage"] = "failed"
            progress["errorCode"] = error.code
            try:
                await self._control.fail(report_run_id, error.code, error.message, progress)
            except ReportExecutionError:
                LOGGER.exception("Could not record Max report failure: %s", report_run_id)
        except Exception:
            LOGGER.exception("Unexpected Max report failure: report_run_id=%s", report_run_id)
            progress["stage"] = "failed"
            progress["errorCode"] = "MAX_REPORT_UNEXPECTED"
            try:
                await self._control.fail(
                    report_run_id,
                    "MAX_REPORT_UNEXPECTED",
                    "The Max report could not be completed. Please retry.",
                    progress,
                )
            except ReportExecutionError:
                LOGGER.exception("Could not record unexpected Max report failure: %s", report_run_id)


_TASKS: dict[str, asyncio.Task[None]] = {}


def start_max_report_task(settings: Settings, report_run_id: str) -> bool:
    existing = _TASKS.get(report_run_id)
    if existing is not None and not existing.done():
        return False
    task = asyncio.create_task(MaxReportExecutor(settings).execute(report_run_id))
    _TASKS[report_run_id] = task

    def cleanup(done: asyncio.Task[None]) -> None:
        _TASKS.pop(report_run_id, None)
        try:
            done.result()
        except Exception:
            LOGGER.exception("Unhandled Max report task exception: %s", report_run_id)

    task.add_done_callback(cleanup)
    return True
