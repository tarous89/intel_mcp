from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from intel_mcp.config import Settings
from intel_mcp.control_plane import ControlPlaneClient, ControlPlaneError
from intel_mcp.engine import EngineClient, EngineError
from intel_mcp.engine_database import DatabaseEngineClient
from intel_mcp.light_report import (
    LIGHT_TRIAL_COUNT,
    LightReportError,
    SelectedTrial,
    SolLightReportRunner,
    light_objectives,
)
from intel_mcp.profiles import FullProfileItem, MAX_PROFILES_PER_CALL


LOGGER = logging.getLogger("intel_mcp")
V3_LIGHT_OBJECTIVE_COUNT = 5
V4_MIN_ANALYSIS_PAIRS = 5
V4_MAX_ANALYSIS_PAIRS = 7


@dataclass(frozen=True)
class ReportExecutionError(Exception):
    code: str
    message: str
    retryable: bool = False


class ReportExecutionControl:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._settings = settings
        self._transport = transport

    async def _post(self, payload: dict[str, Any], timeout: float = 20) -> dict[str, Any]:
        self._settings.validate_control_plane()
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
                response = await client.post(
                    f"{self._settings.app_control_url}/api/internal/report-execution",
                    headers={"Authorization": f"Bearer {self._settings.app_service_token}"},
                    json=payload,
                )
        except httpx.HTTPError as error:
            raise ReportExecutionError(
                "REPORT_CONTROL_UNAVAILABLE",
                "The report control plane is unavailable.",
                True,
            ) from error
        try:
            body = response.json()
        except ValueError as error:
            raise ReportExecutionError(
                "REPORT_CONTROL_INVALID_RESPONSE",
                "The report control plane returned invalid JSON.",
                True,
            ) from error
        if response.status_code >= 400:
            error_body = body.get("error") if isinstance(body, dict) else None
            code = (
                str(error_body.get("code") or "REPORT_CONTROL_FAILED")
                if isinstance(error_body, dict)
                else "REPORT_CONTROL_FAILED"
            )
            message = (
                str(error_body.get("message") or "The report control request failed.")
                if isinstance(error_body, dict)
                else "The report control request failed."
            )
            raise ReportExecutionError(code, message, response.status_code >= 500)
        if not isinstance(body, dict):
            raise ReportExecutionError(
                "REPORT_CONTROL_INVALID_RESPONSE",
                "The report control plane returned an invalid response.",
                True,
            )
        return body

    async def load(self, report_run_id: str) -> dict[str, Any]:
        return await self._post({"action": "load", "reportRunId": report_run_id})

    async def progress(self, report_run_id: str, progress: dict[str, Any]) -> None:
        await self._post({"action": "progress", "reportRunId": report_run_id, "progress": progress})

    async def complete(
        self,
        report_run_id: str,
        progress: dict[str, Any],
        final_report: dict[str, Any],
    ) -> None:
        await self._post(
            {
                "action": "complete",
                "reportRunId": report_run_id,
                "progress": progress,
                "finalReport": final_report,
            }
        )

    async def fail(self, report_run_id: str, code: str, message: str, progress: dict[str, Any]) -> None:
        await self._post(
            {
                "action": "fail",
                "reportRunId": report_run_id,
                "errorCode": code,
                "errorMessage": message,
                "progress": progress,
            }
        )


def prioritize_light_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Preserve the v2 Light ordering contract for already-approved legacy plans."""
    if plan.get("version") in {3, 4}:
        return plan
    sections = plan.get("reportSections")
    if not isinstance(sections, list):
        return plan

    indexed = list(enumerate(sections))

    def priority(item: tuple[int, Any]) -> tuple[int, int, int]:
        index, section = item
        if not isinstance(section, dict):
            return (2, 1, index)
        max_only = 1 if section.get("maxOnly") is True else 0
        coverage = 0 if section.get("coverage") == "strong" else 1
        return (max_only, coverage, index)

    ordered_sections = [section for _, section in sorted(indexed, key=priority)]
    return {**plan, "reportSections": ordered_sections}


def _v3_light_execution_view(plan: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Project a v3 plan onto its legacy five-objective Light contract."""
    cohorts = plan.get("studyCohorts")
    sections = plan.get("reportSections")
    if not isinstance(cohorts, list) or len(cohorts) < 3 or not isinstance(cohorts[0], dict):
        raise ReportExecutionError(
            "LIGHT_REPORT_PLAN_INVALID",
            "The v3 plan has no valid shared trial group.",
            False,
        )
    if cohorts[0].get("role") != "primary" or cohorts[0].get("maxOnly") is not False:
        raise ReportExecutionError(
            "LIGHT_REPORT_PLAN_INVALID",
            "The v3 shared trial group is invalid.",
            False,
        )
    if not isinstance(sections, list) or len(sections) < V3_LIGHT_OBJECTIVE_COUNT:
        raise ReportExecutionError(
            "LIGHT_REPORT_PLAN_INVALID",
            "The v3 plan has too few objectives.",
            False,
        )

    objectives: list[dict[str, Any]] = []
    for raw in sections[:V3_LIGHT_OBJECTIVE_COUNT]:
        if not isinstance(raw, dict):
            raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "A v3 report objective is invalid.", False)
        title = raw.get("title")
        analyses = raw.get("analyses")
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(analyses, list)
            or len(analyses) < 3
        ):
            raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "A v3 report objective is invalid.", False)
        first = analyses[0]
        if not isinstance(first, str) or not first.strip():
            raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "A v3 shared analysis is invalid.", False)
        objectives.append({"title": title.strip(), "analyses": [first.strip()]})

    selection_sections = [
        {"title": item["title"], "analyses": list(item["analyses"])}
        for item in objectives[:3]
    ]
    for index, extra in enumerate(objectives[3:]):
        selection_sections[index]["analyses"].append(f"{extra['title']}: {extra['analyses'][0]}")

    selection_plan = {
        "version": 3,
        "studyCohorts": [cohorts[0]],
        "exclusionSummary": plan.get("exclusionSummary"),
        "reportSections": selection_sections,
    }
    return selection_plan, objectives


def _v4_light_execution_view(plan: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Project paired v4 planning onto the shared Light layer only.

    Every v4 pair has one shared analysis and one Max analysis. Light executes every
    shared analysis (5-7), never the paired Max analysis, and searches only the first
    single-dimension shared trial group. Selection receives compact summaries of every
    shared analysis so the frozen 20-trial cohort remains useful across the whole Light
    report without exposing any Max-only criteria to selection.
    """
    cohorts = plan.get("studyCohorts")
    sections = plan.get("reportSections")
    if not isinstance(cohorts, list) or len(cohorts) < 3 or not isinstance(cohorts[0], dict):
        raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "The v4 plan has no valid shared trial group.", False)
    shared = cohorts[0]
    if (
        shared.get("role") != "primary"
        or shared.get("maxOnly") is not False
        or shared.get("filterDimension") not in {"disease", "therapeutic_area", "phase", "modality", "country"}
    ):
        raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "The v4 shared trial group is invalid.", False)
    if not isinstance(sections, list) or not V4_MIN_ANALYSIS_PAIRS <= len(sections) <= V4_MAX_ANALYSIS_PAIRS:
        raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "The v4 plan has an invalid number of analysis pairs.", False)

    objectives: list[dict[str, Any]] = []
    selection_requirements: list[str] = []
    for raw in sections:
        if not isinstance(raw, dict):
            raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "A v4 analysis pair is invalid.", False)
        title = raw.get("title")
        shared_analysis = raw.get("sharedAnalysis")
        max_analysis = raw.get("maxAnalysis")
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(shared_analysis, dict)
            or not isinstance(max_analysis, dict)
        ):
            raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "A v4 analysis pair is invalid.", False)
        shared_title = shared_analysis.get("title")
        details = shared_analysis.get("details")
        if (
            not isinstance(shared_title, str)
            or not shared_title.strip()
            or title.strip() != shared_title.strip()
            or not isinstance(details, list)
            or not 1 <= len(details) <= 4
        ):
            raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "A v4 shared analysis is invalid.", False)
        cleaned_details = [item.strip() for item in details if isinstance(item, str) and item.strip()]
        if len(cleaned_details) != len(details):
            raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "A v4 shared analysis is invalid.", False)
        objectives.append({"title": shared_title.strip(), "analyses": cleaned_details})
        selection_requirements.append(f"{shared_title.strip()}: {'; '.join(cleaned_details)}")

    # The legacy selector helper reads at most three objective containers. Distribute
    # all 5-7 shared requirements across three compact containers; each container stays
    # within the helper's four-analysis cap. Max titles/details are deliberately absent.
    selection_sections = [
        {"title": f"Shared evidence needs {index + 1}", "analyses": []}
        for index in range(3)
    ]
    for index, requirement in enumerate(selection_requirements):
        selection_sections[index % 3]["analyses"].append(requirement)

    selection_plan = {
        "version": 4,
        "studyCohorts": [shared],
        "exclusionSummary": plan.get("exclusionSummary"),
        "reportSections": selection_sections,
    }
    return selection_plan, objectives


def _light_execution_view(plan: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if plan.get("version") == 4:
        return _v4_light_execution_view(plan)
    if plan.get("version") == 3:
        return _v3_light_execution_view(plan)
    prioritized = prioritize_light_plan(plan)
    return prioritized, light_objectives(prioritized)


def _analyzed_cohort_summary(
    plan: dict[str, Any],
    selected_trials: list[SelectedTrial],
) -> dict[str, Any]:
    """Summarize the exact frozen evidence cohort without exposing trial identities."""
    cohorts = plan.get("studyCohorts")
    if not isinstance(cohorts, list) or not cohorts:
        raise ReportExecutionError(
            "LIGHT_REPORT_PLAN_INVALID",
            "The approved plan has no study cohorts.",
            False,
        )

    buckets: list[dict[str, Any]] = []
    for index, raw in enumerate(cohorts):
        if not isinstance(raw, dict):
            raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "A study cohort is invalid.", False)
        title = raw.get("title")
        role = raw.get("role")
        if not isinstance(title, str) or not title.strip() or role not in {"primary", "adjacent"}:
            raise ReportExecutionError("LIGHT_REPORT_PLAN_INVALID", "A study cohort is invalid.", False)
        buckets.append(
            {
                "title": title.strip(),
                "role": role,
                "trialCount": sum(1 for item in selected_trials if item.cohort_index == index),
            }
        )

    if sum(bucket["trialCount"] for bucket in buckets) != len(selected_trials):
        raise ReportExecutionError(
            "LIGHT_REPORT_EVIDENCE_SET_INVALID",
            "The selected trials do not map cleanly to the approved study cohorts.",
            False,
        )
    return {"totalTrials": len(selected_trials), "cohorts": buckets}


def _steps(objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"key": "trial_selection", "label": "Finding the best 20 trials", "status": "waiting"},
        *[
            {
                "key": f"objective_{index + 1}",
                "label": f"Analyzing {objective['title']}",
                "status": "waiting",
            }
            for index, objective in enumerate(objectives)
        ],
        {"key": "final_report", "label": "Preparing final report", "status": "waiting"},
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
        if step.get("key") == key:
            step["status"] = status
            if completed_units is not None:
                step["completedUnits"] = completed_units
            if total_units is not None:
                step["totalUnits"] = total_units
            break
    completed = sum(1 for step in next_progress["steps"] if step.get("status") == "completed")
    next_progress["completedSteps"] = completed
    next_progress["totalSteps"] = len(next_progress["steps"])
    next_progress["stage"] = key
    return next_progress


class LightReportExecutor:
    def __init__(
        self,
        settings: Settings,
        *,
        openai_transport: httpx.AsyncBaseTransport | None = None,
        control_transport: httpx.AsyncBaseTransport | None = None,
        engine_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._runner = SolLightReportRunner(settings, transport=openai_transport)
        self._control = ReportExecutionControl(settings, transport=control_transport)
        self._analysis_control = ControlPlaneClient(settings, transport=control_transport)
        self._engine: EngineClient | DatabaseEngineClient = (
            DatabaseEngineClient(settings)
            if settings.engine_source == "database"
            else EngineClient(settings, transport=engine_transport)
        )

    async def _load_complete_evidence_profiles(
        self,
        analysis_id: str,
        selected_trials: list[SelectedTrial],
    ) -> list[FullProfileItem]:
        """Fetch the complete frozen evidence cohort once, outside model tool use."""
        trial_ids = [item.trial_id for item in selected_trials]
        if len(trial_ids) != LIGHT_TRIAL_COUNT or len(set(trial_ids)) != LIGHT_TRIAL_COUNT:
            raise ReportExecutionError(
                "LIGHT_REPORT_EVIDENCE_SET_INVALID",
                "The selected Light evidence set is invalid.",
                False,
            )

        profiles: list[FullProfileItem] = []
        for start in range(0, len(trial_ids), MAX_PROFILES_PER_CALL):
            batch = trial_ids[start:start + MAX_PROFILES_PER_CALL]
            try:
                engine_result = await self._engine.get_profiles(batch)
                if engine_result.unavailable_trial_ids:
                    raise ReportExecutionError(
                        "LIGHT_REPORT_PROFILE_UNAVAILABLE",
                        "One or more selected Trial Profiles are no longer available.",
                        True,
                    )
                access_result = await self._analysis_control.authorize_profiles(
                    analysis_id,
                    [item.eu_number for item in engine_result.data],
                )
            except ControlPlaneError as error:
                raise ReportExecutionError(error.code, error.message, error.status_code >= 500) from error
            except EngineError as error:
                raise ReportExecutionError(error.code, error.message, error.status_code >= 500) from error

            returned_ids = [item.eu_number for item in engine_result.data]
            if returned_ids != batch or access_result.access.allowed_trial_ids != batch:
                raise ReportExecutionError(
                    "LIGHT_REPORT_PROFILE_ACCESS_INCOMPLETE",
                    "The complete selected Trial Profiles could not all be authorized.",
                    True,
                )
            profiles.extend(engine_result.data)

        if [item.eu_number for item in profiles] != trial_ids:
            raise ReportExecutionError(
                "LIGHT_REPORT_EVIDENCE_INCOMPLETE",
                "The complete 20-profile evidence bundle is incomplete.",
                True,
            )
        return profiles

    async def execute(self, report_run_id: str) -> None:
        progress: dict[str, Any] = {
            "version": 1,
            "stage": "starting",
            "completedSteps": 0,
            "totalSteps": 5,
            "steps": [],
        }
        try:
            job = await self._control.load(report_run_id)
            if job.get("status") == "completed":
                return
            if job.get("tier") != "light":
                raise ReportExecutionError(
                    "LIGHT_REPORT_TIER_REQUIRED",
                    "This executor only supports Light reports.",
                    False,
                )
            context = job.get("context")
            insights = job.get("insights")
            approved_plan = job.get("plan")
            if not isinstance(context, str) or not isinstance(insights, str) or not isinstance(approved_plan, dict):
                raise ReportExecutionError(
                    "LIGHT_REPORT_JOB_INVALID",
                    "The Light report job is missing its approved plan or brief.",
                    False,
                )

            selection_plan, objectives = _light_execution_view(approved_plan)
            progress = {
                "version": 1,
                "stage": "starting",
                "completedSteps": 0,
                "totalSteps": len(objectives) + 2,
                "steps": _steps(objectives),
                "selectedTrials": [],
                "sectionsCompleted": 0,
            }
            await self._control.progress(report_run_id, progress)

            try:
                access = await self._analysis_control.start_analysis(report_run_id)
            except ControlPlaneError as error:
                raise ReportExecutionError(error.code, error.message, error.status_code >= 500) from error
            analysis_id = access.analysis.analysis_id

            progress = _mark(progress, "trial_selection", "in_progress", completed_units=0, total_units=20)
            await self._control.progress(report_run_id, progress)
            selection = await self._runner.select_trials(
                analysis_id=analysis_id,
                context=context,
                insights=insights,
                plan=selection_plan,
            )
            selected = [item.model_dump() for item in selection.selected_trials]
            progress["selectedTrials"] = selected
            progress = _mark(progress, "trial_selection", "completed", completed_units=20, total_units=20)
            await self._control.progress(report_run_id, progress)

            full_profiles = await self._load_complete_evidence_profiles(
                analysis_id,
                selection.selected_trials,
            )

            section_results = []
            for index, objective in enumerate(objectives):
                key = f"objective_{index + 1}"
                progress = _mark(progress, key, "in_progress")
                await self._control.progress(report_run_id, progress)
                section = await self._runner.analyze_objective(
                    context=context,
                    objective=objective,
                    selected_trials=selection.selected_trials,
                    full_profiles=full_profiles,
                )
                section_results.append(section)
                progress["sectionsCompleted"] = len(section_results)
                progress["sections"] = [item.model_dump() for item in section_results]
                progress = _mark(progress, key, "completed")
                await self._control.progress(report_run_id, progress)

            progress = _mark(progress, "final_report", "in_progress")
            await self._control.progress(report_run_id, progress)
            synthesis = await self._runner.synthesize(
                context=context,
                selection=selection,
                sections=section_results,
            )
            progress = _mark(progress, "final_report", "completed")
            progress["stage"] = "completed"
            final_report = {
                "version": 2,
                "tier": "light",
                "title": synthesis.title,
                "executiveSummary": synthesis.executive_summary,
                "analyzedCohort": _analyzed_cohort_summary(selection_plan, selection.selected_trials),
                "closingNote": synthesis.closing_note,
                "sections": [item.model_dump() for item in section_results],
            }
            await self._control.complete(report_run_id, progress, final_report)
        except (LightReportError, ReportExecutionError) as error:
            LOGGER.exception("Light report failed: report_run_id=%s code=%s", report_run_id, error.code)
            progress["stage"] = "failed"
            progress["errorCode"] = error.code
            try:
                await self._control.fail(report_run_id, error.code, error.message, progress)
            except ReportExecutionError:
                LOGGER.exception("Could not record Light report failure: %s", report_run_id)
        except Exception:
            LOGGER.exception("Unexpected Light report failure: report_run_id=%s", report_run_id)
            progress["stage"] = "failed"
            progress["errorCode"] = "LIGHT_REPORT_UNEXPECTED"
            try:
                await self._control.fail(
                    report_run_id,
                    "LIGHT_REPORT_UNEXPECTED",
                    "The report could not be completed. Please retry.",
                    progress,
                )
            except ReportExecutionError:
                LOGGER.exception("Could not record unexpected Light report failure: %s", report_run_id)


_TASKS: dict[str, asyncio.Task[None]] = {}


def start_light_report_task(settings: Settings, report_run_id: str) -> bool:
    existing = _TASKS.get(report_run_id)
    if existing is not None and not existing.done():
        return False
    task = asyncio.create_task(LightReportExecutor(settings).execute(report_run_id))
    _TASKS[report_run_id] = task

    def cleanup(done: asyncio.Task[None]) -> None:
        _TASKS.pop(report_run_id, None)
        try:
            done.result()
        except Exception:
            LOGGER.exception("Unhandled Light report task exception: %s", report_run_id)

    task.add_done_callback(cleanup)
    return True
