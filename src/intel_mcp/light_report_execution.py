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
            code = str(error_body.get("code") or "REPORT_CONTROL_FAILED") if isinstance(error_body, dict) else "REPORT_CONTROL_FAILED"
            message = str(error_body.get("message") or "The report control request failed.") if isinstance(error_body, dict) else "The report control request failed."
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
    """Return a stable execution view that gives strong coverage the Light slots first.

    Planner-declared Max-only objectives remain Max regardless of coverage. Among the
    remaining profile-eligible objectives, strong coverage precedes source-dependent
    coverage while preserving the planner's order inside each bucket.
    """
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
        """Fetch the complete frozen evidence cohort once, outside model tool use.

        The read remains subject to the normal app-owned profile allowance. Because
        selection section reads are ID-idempotent, later full reads of the same trial
        do not consume a second profile unit.
        """
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
            plan = job.get("plan")
            if not isinstance(context, str) or not isinstance(insights, str) or not isinstance(plan, dict):
                raise ReportExecutionError(
                    "LIGHT_REPORT_JOB_INVALID",
                    "The Light report job is missing its approved plan or brief.",
                    False,
                )
            # Light slots are evidence-prioritized rather than assigned by original row order:
            # planner-declared Max-only objectives stay Max, then strong profile-eligible
            # objectives take precedence over source-dependent profile-eligible objectives.
            plan = prioritize_light_plan(plan)
            objectives = light_objectives(plan)
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
                plan=plan,
            )
            selected = [item.model_dump() for item in selection.selected_trials]
            progress["selectedTrials"] = selected
            progress = _mark(progress, "trial_selection", "completed", completed_units=20, total_units=20)
            await self._control.progress(report_run_id, progress)

            # Freeze and load the 20 complete profiles once. Objective model calls receive
            # this same in-context evidence bundle directly and have no MCP tools.
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
