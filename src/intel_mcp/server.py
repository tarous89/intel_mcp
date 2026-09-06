from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime, timezone
from functools import wraps
from inspect import signature
from typing import Annotated
from uuid import uuid4

import uvicorn
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from intel_mcp.auth_context import reset_oauth_subject, set_oauth_subject
from intel_mcp.classification import (
    ClassifierError,
    ClassificationCounts,
    ClassifyTrialsOutput,
    aggregate_trial_result,
    classification_key,
    classify_profile_items,
    validate_criteria,
)
from intel_mcp.config import Settings
from intel_mcp.control_plane import ControlPlaneClient, ControlPlaneError
from intel_mcp.documents import GetDocumentsOutput
from intel_mcp.docs_site import DOCS_HTML
from intel_mcp.engine import EngineClient, EngineError
from intel_mcp.engine_database import DatabaseEngineClient
from intel_mcp.extraction import (
    MAX_VARIABLES_PER_CALL,
    ExtractVariablesOutput,
    ExtractionVariable,
    ExtractorError,
    TerraExtractor,
    extraction_key,
    normalize_variables,
)
from intel_mcp.models import (
    AnalysisAllowance,
    AnalysisLimits,
    FilterCounts,
    FilterTrialsOutput,
    StartAnalysisOutput,
    TrialFilters,
    TrialSort,
)
from intel_mcp.profiles import (
    MAX_PROFILES_PER_CALL,
    PROFILE_SECTIONS,
    GetProfilesCounts,
    GetProfilesOutput,
    ProfileSection,
    normalize_profile_sections,
    project_profile,
)
from intel_mcp.report_plan import ReportPlanError, SolReportPlanner
from intel_mcp.telemetry import begin_metrics, end_metrics, set_worker_model

LOGGER = logging.getLogger("intel_mcp")
OAUTH_SCOPE = "mcp:tools"
OAUTH_TOOL_META = {"securitySchemes": [{"type": "oauth2", "scopes": [OAUTH_SCOPE]}]}

settings = Settings.from_environment()
mcp = MCPServer(
    "TrialAgents Intel MCP",
    instructions=(
        "Use start_analysis once after the Intel Agent app has created an approved report run. "
        "Pass the returned analysis_id to every later Intel tool. Use filter_trials for broad structured "
        "screening. When reviewing shortlisted trials, call get_profiles with only the profile sections "
        "needed for the task; omit sections when the complete profile is required."
    ),
)


def control_plane_client() -> ControlPlaneClient:
    return ControlPlaneClient(settings)


_engine_reader: EngineClient | DatabaseEngineClient | None = None


def engine_client() -> EngineClient | DatabaseEngineClient:
    global _engine_reader
    if _engine_reader is None:
        _engine_reader = (
            DatabaseEngineClient(settings)
            if settings.engine_source == "database"
            else EngineClient(settings)
        )
    return _engine_reader


def track_tool_call(tool_name: str):
    def decorate(function):
        function_signature = signature(function)

        @wraps(function)
        async def wrapped(*args, **kwargs):
            bound = function_signature.bind_partial(*args, **kwargs)
            analysis_id = bound.arguments.get("analysis_id")
            report_run_id = bound.arguments.get("report_run_id")
            started_at = datetime.now(timezone.utc)
            started_clock = time.perf_counter()
            metrics, metrics_token = begin_metrics()
            status = "success"
            error_code = None
            try:
                return await function(*args, **kwargs)
            except Exception as error:
                status = "error"
                message = str(error)
                error_code = message.split(":", 1)[0][:100] if message else error.__class__.__name__[:100]
                raise
            finally:
                completed_at = datetime.now(timezone.utc)
                duration_ms = max(0, round((time.perf_counter() - started_clock) * 1000))
                end_metrics(metrics_token)
                payload = {
                    "callId": str(uuid4()),
                    "toolName": tool_name,
                    "status": status,
                    "workerCalls": metrics.worker_calls,
                    "inputTokens": metrics.input_tokens,
                    "cachedInputTokens": metrics.cached_input_tokens,
                    "outputTokens": metrics.output_tokens,
                    "reasoningTokens": metrics.reasoning_tokens,
                    "totalTokens": metrics.total_tokens,
                    "startedAt": started_at.isoformat(),
                    "completedAt": completed_at.isoformat(),
                    "durationMs": duration_ms,
                }
                if isinstance(analysis_id, str):
                    payload["analysisId"] = analysis_id
                if isinstance(report_run_id, str):
                    payload["reportRunId"] = report_run_id
                if error_code:
                    payload["errorCode"] = error_code
                if metrics.worker_model:
                    payload["workerModel"] = metrics.worker_model
                try:
                    await control_plane_client().record_tool_call(payload)
                except Exception:
                    LOGGER.warning("MCP telemetry delivery failed for %s", tool_name, exc_info=True)

        return wrapped

    return decorate


@mcp.tool(
    title="Start Intel analysis",
    meta=OAUTH_TOOL_META,
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
@track_tool_call("start_analysis")
async def start_analysis(
    report_run_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=128,
            description="Stable report run ID created by the authenticated Intel Agent app after plan approval.",
        ),
    ],
) -> StartAnalysisOutput:
    """Reserve or recover the current user's one active 60-minute analysis lease.

    This lifecycle tool performs no trial filtering, retrieval, classification, extraction or report writing.
    Identity, plan approval, package, enabled tools and remaining allowance are resolved by the app control plane.
    Repeating the call while the user has an active analysis returns that existing lease without another charge.
    """
    try:
        response = await control_plane_client().start_analysis(report_run_id)
    except ControlPlaneError as error:
        raise ToolError(f"{error.code}: {error.message}") from error

    analysis = response.analysis
    return StartAnalysisOutput(
        analysis_id=analysis.analysis_id,
        report_run_id=analysis.report_run_id,
        tier=analysis.tier,
        expires_at=analysis.expires_at,
        enabled_tools=analysis.enabled_tools,
        limits=AnalysisLimits.model_validate(analysis.limits.model_dump()),
        reused=analysis.reused,
    )


@mcp.tool(
    title="Filter approved clinical trials",
    meta=OAUTH_TOOL_META,
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
@track_tool_call("filter_trials")
async def filter_trials(
    analysis_id: Annotated[
        str,
        Field(
            min_length=20,
            max_length=128,
            description="Active 60-minute analysis ID returned by start_analysis.",
        ),
    ],
    filters: Annotated[
        TrialFilters,
        Field(
            description=(
                "Structured Trial Profile filters. Text matching is case-insensitive; contains is "
                "the default and is is exact after case folding. Different fields combine with AND. "
                "Use one contains_any/contains_all list for multiple values in the same field. Make "
                "separate calls when OR is required across different fields. Missing values never "
                "satisfy negative operators."
            )
        ),
    ],
    sort: Annotated[
        TrialSort,
        Field(description="Deterministic sort. The EU trial number is always the stable tie-breaker."),
    ] = TrialSort(),
    limit: Annotated[
        int,
        Field(
            ge=1,
            le=100,
            description="Maximum trials requested in this page. The hard per-call cap is 100.",
        ),
    ] = 20,
    offset: Annotated[
        int,
        Field(
            ge=0,
            le=1_000_000,
            description="Number of matching trials to skip. Use 0 for the first page, then add the prior limit.",
        ),
    ] = 0,
) -> FilterTrialsOutput:
    """Deterministically shortlist approved structured Trial Profiles.

    Use this as the first screening step to reduce the candidate set with broad, reliable structured
    conditions. After shortlisting, use classify_trials for complex inclusion/exclusion conditions that
    require semantic interpretation of the Trial Profile. Do not use broad classification as the initial
    discovery step when structured filtering can first reduce the candidate pool.

    This tool queries only documented structured columns. It does not search the complete profile,
    run semantic search, classify trials, retrieve full profiles/documents, extract variables, or
    write a report. Sponsor-name matching is a shortlist aid: the CTIS source can sometimes identify
    a subsidy/funding source or omit part of the complete legal entity name.

    Results are validated and metered against the app-owned analysis lease. Light analyses may see
    at most 100 unique filtered trial IDs and Max analyses at most 1,000; retries and revisions do not
    consume the same trial ID twice. For another page, repeat the same filters and sort with offset
    increased by the prior call's limit.
    """
    try:
        engine_result = await engine_client().filter_trials(
            filters=filters,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        access_result = await control_plane_client().authorize_filter_results(
            analysis_id,
            [item.eu_number for item in engine_result.data],
        )
    except (ControlPlaneError, EngineError) as error:
        raise ToolError(f"{error.code}: {error.message}") from error

    access = access_result.access
    allowed = set(access.allowed_trial_ids)
    data = [item for item in engine_result.data if item.eu_number in allowed]
    return FilterTrialsOutput(
        data=data,
        counts=FilterCounts(
            total_profiles=engine_result.counts.total_profiles,
            total_matches=engine_result.counts.total_matches,
            returned=len(data),
        ),
        analysis_allowance=AnalysisAllowance(
            limit=access.limit,
            used=access.used,
            remaining=access.remaining,
        ),
    )


@mcp.tool(
    title="Classify approved clinical trials",
    meta=OAUTH_TOOL_META,
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
@track_tool_call("classify_trials")
async def classify_trials(
    analysis_id: Annotated[
        str,
        Field(
            min_length=20,
            max_length=128,
            description="Active 60-minute analysis ID returned by start_analysis.",
        ),
    ],
    trial_ids: Annotated[
        list[Annotated[str, Field(pattern=r"^\d{4}-\d{6}-\d{2}-\d{2}$")]],
        Field(
            min_length=1,
            max_length=25,
            description="One to 25 distinct EU trial numbers with approved Trial Profiles.",
        ),
    ],
    inclusion_criteria: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=600)]],
        Field(
            min_length=1,
            max_length=20,
            description=(
                "One or more user-defined trial classification conditions that must all be true for eligibility. "
                "These are analysis criteria, not necessarily formal protocol inclusion criteria."
            ),
        ),
    ],
    exclusion_criteria: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=600)]],
        Field(
            min_length=1,
            max_length=20,
            description=(
                "One or more user-defined exclusionary conditions that must all be false for eligibility. "
                "A true classifier answer means the exclusionary condition is present."
            ),
        ),
    ],
) -> ClassifyTrialsOutput:
    """Classify selected approved Trial Profiles into eligible, ineligible or uncertain trial IDs.

    Use this as the final semantic classification step for trials already shortlisted with filter_trials.
    Do not classify a broad discovery population when structured filtering can first reduce it. Classify
    at most 25 trials per call; split a larger shortlist into batches using the same criteria.

    One independent Terra worker call is made per trial. Inside each worker call, every inclusion and
    exclusion criterion is classified separately as true, false or unknown/null with concise evidence.
    Those detailed criterion-level results stay internal to the worker/aggregation path and are not
    returned by this MCP tool.

    Deterministic aggregation is:
    - ineligible if ANY inclusion criterion is false OR ANY exclusion criterion is true;
    - otherwise uncertain if ANY criterion is unknown/null;
    - otherwise eligible (all inclusions true and all exclusions false).

    Criteria are interpreted literally. Inclusion/exclusion labels never invert Terra's boolean answer.
    Normally, missing information produces unknown and therefore an uncertain trial. Only when it is
    analytically appropriate may the caller explicitly include unknown/missing information in the wording
    of an individual criterion, for example "pediatric patients are included OR pediatric participation is
    unknown". In that example an unknown pediatric status makes that complete criterion true. Do not add
    unknown handling routinely; use it only when the analysis genuinely intends that behavior.

    The tool uses complete approved Trial Profile 10.0.0 objects, including document inventory and results,
    with contact personal data removed. It does not retrieve or inspect protocol/document text and does not
    use external knowledge. If a needed fact is absent from the Trial Profile, ordinary criteria stay unknown.
    """
    if len(set(trial_ids)) != len(trial_ids):
        raise ToolError("INVALID_TRIAL_IDS: trial_ids must not contain duplicates.")
    try:
        inclusion, exclusion = validate_criteria(inclusion_criteria, exclusion_criteria)
    except ValueError as error:
        raise ToolError(f"INVALID_CRITERIA: {error}") from error

    keys = [classification_key(trial_id, inclusion, exclusion) for trial_id in trial_ids]
    control = control_plane_client()
    try:
        # Validate approved-profile availability before reserving classification allowance.
        profile_result = await engine_client().classification_profiles(trial_ids)
        access_result = await control.authorize_classifications(analysis_id, keys, "reserve")
    except (ControlPlaneError, EngineError) as error:
        raise ToolError(f"{error.code}: {error.message}") from error

    if access_result.access.allowed_classification_keys != keys:
        raise ToolError(
            "CLASSIFICATION_ACCESS_FAILED: the control plane returned misaligned classification authorization."
        )

    set_worker_model(access_result.access.worker_model)

    try:
        worker_results = await classify_profile_items(
            settings,
            profile_result.data,
            inclusion,
            exclusion,
            model=access_result.access.worker_model,
        )
    except ClassifierError as error:
        try:
            await control.authorize_classifications(analysis_id, keys, "release")
        except ControlPlaneError:
            pass
        raise ToolError(f"{error.code}: {error.message}") from error
    except Exception:
        try:
            await control.authorize_classifications(analysis_id, keys, "release")
        except ControlPlaneError:
            pass
        raise

    try:
        commit_result = await control.authorize_classifications(analysis_id, keys, "commit")
    except ControlPlaneError as error:
        raise ToolError(f"{error.code}: {error.message}") from error

    eligible_trials: list[str] = []
    ineligible_trials: list[str] = []
    uncertain_trials: list[str] = []
    for result in worker_results:
        classification = aggregate_trial_result(result)
        if classification == "eligible":
            eligible_trials.append(result.trial_id)
        elif classification == "ineligible":
            ineligible_trials.append(result.trial_id)
        else:
            uncertain_trials.append(result.trial_id)

    return ClassifyTrialsOutput(
        eligible_trials=eligible_trials,
        ineligible_trials=ineligible_trials,
        uncertain_trials=uncertain_trials,
        counts=ClassificationCounts(
            classified=len(worker_results),
            eligible=len(eligible_trials),
            ineligible=len(ineligible_trials),
            uncertain=len(uncertain_trials),
        ),
        analysis_allowance=AnalysisAllowance(
            limit=commit_result.access.limit,
            used=commit_result.access.used,
            remaining=commit_result.access.remaining,
        ),
    )


@mcp.tool(
    title="Get approved Trial Profile data",
    meta=OAUTH_TOOL_META,
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
@track_tool_call("get_profiles")
async def get_profiles(
    analysis_id: Annotated[
        str,
        Field(
            min_length=20,
            max_length=128,
            description="Active 60-minute analysis ID returned by start_analysis.",
        ),
    ],
    trial_ids: Annotated[
        list[Annotated[str, Field(pattern=r"^\d{4}-\d{6}-\d{2}-\d{2}$")]],
        Field(
            min_length=1,
            max_length=MAX_PROFILES_PER_CALL,
            description="One to 10 EU trial numbers. Duplicate values are removed while preserving order.",
        ),
    ],
    sections: Annotated[
        list[ProfileSection] | None,
        Field(
            max_length=len(PROFILE_SECTIONS),
            description=(
                "Optional Trial Profile 10.0.0 sections. Choose only what the task needs. Supported values: "
                "overview, population, trial_design, interventions, eligibility, objectives, endpoints, "
                "sponsor_and_organizations, contacts, countries, sites, documents, lifecycle, results. "
                "Omit or pass [] to return complete profiles."
            ),
        ),
    ] = None,
) -> GetProfilesOutput:
    """Return approved Trial Profiles in full or as exact section projections.

    Every call accepts up to ten trial IDs, whether sections are requested or complete profiles are requested.
    Section mode is a deterministic projection of the stored approved profile: it preserves the original
    field values and nesting and performs no model summarization. Omit sections (or pass an empty list) to
    return the complete approved profile.

    The section vocabulary follows Trial Profile 10.0.0. Candidate and rejected profiles are treated as
    unavailable; there is no raw-CTIS fallback. The tool does not generate or refresh profiles, retrieve
    document text, classify trials, search semantically, or write report prose. Exact retries or later
    retrieval of the same profile do not consume the analysis allowance twice.
    """
    unique_trial_ids = list(dict.fromkeys(trial_ids))
    selected_sections = normalize_profile_sections(sections)

    try:
        engine_result = await engine_client().get_profiles(unique_trial_ids)
        available_ids = [item.eu_number for item in engine_result.data]
        access_result = await control_plane_client().authorize_profiles(analysis_id, available_ids)
    except (ControlPlaneError, EngineError) as error:
        raise ToolError(f"{error.code}: {error.message}") from error

    access = access_result.access
    allowed = set(access.allowed_trial_ids)
    if not allowed.issubset(available_ids) or len(allowed) != len(access.allowed_trial_ids):
        raise ToolError("PROFILE_ACCESS_FAILED: the control plane returned misaligned profile authorization.")

    profiles = [
        item.model_copy(update={"profile": project_profile(item.profile, selected_sections)}, deep=True)
        for item in engine_result.data
        if item.eu_number in allowed
    ]
    allowance_reached = [item.eu_number for item in engine_result.data if item.eu_number not in allowed]

    return GetProfilesOutput(
        profiles=profiles,
        unavailable_trial_ids=engine_result.unavailable_trial_ids,
        allowance_reached_trial_ids=allowance_reached,
        counts=GetProfilesCounts(
            requested=len(unique_trial_ids),
            returned=len(profiles),
            unavailable=len(engine_result.unavailable_trial_ids),
            allowance_reached=len(allowance_reached),
        ),
        analysis_allowance=AnalysisAllowance(
            limit=access.limit,
            used=access.used,
            remaining=access.remaining,
        ),
    )


@mcp.tool(
    title="Get extracted CTIS document text",
    meta=OAUTH_TOOL_META,
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
@track_tool_call("get_documents")
async def get_documents(
    analysis_id: Annotated[
        str,
        Field(
            min_length=20,
            max_length=128,
            description="Active 60-minute analysis ID returned by start_analysis.",
        ),
    ],
    trial_id: Annotated[
        str,
        Field(
            pattern=r"^\d{4}-\d{6}-\d{2}-\d{2}$",
            description="EU trial number with a current approved Trial Profile.",
        ),
    ],
    document_name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=1000,
            description=(
                "One exact document name from an approved Trial Profile's "
                "filtering_variables.available_extracted_documents arrays, returned by "
                "get_profiles. Matching is case-insensitive."
            ),
        ),
    ],
    part: Annotated[
        int,
        Field(
            ge=1,
            le=10_000,
            description=(
                "One-based document part. Start with 1. If next_part is not null, repeat the same "
                "call using that value until next_part is null."
            ),
        ),
    ] = 1,
) -> GetDocumentsOutput:
    """Return extracted text for one explicitly named CTIS document.

    Use this tool for deep source review or page-cited verification after trial shortlisting or
    classification. Request exactly one document name per call. The response contains text only,
    with page markers retained inside the text; it never returns a PDF, binary, download link,
    page count or character count.

    Each numbered part contains at most 200,000 characters. Start with part 1 and continue with
    the returned next_part until it is null. Additional parts of the same document do not consume
    additional document allowance. Exact retries are allowance-idempotent.

    Exact filenames are available in the complete Trial Profile returned by get_profiles. Only successfully
    or partially extracted documents listed in one of that profile's six
    filtering_variables.available_extracted_documents arrays are accessible. The tool performs no download,
    OCR, extraction, semantic search or model work.
    For targeted facts, use extract_variables instead of loading many complete documents into
    the model context.
    """
    try:
        engine_result = await engine_client().get_document(
            trial_id=trial_id,
            document_name=document_name,
            part=part,
        )
        access_result = await control_plane_client().authorize_document(
            analysis_id,
            engine_result.document_access_key,
        )
    except (ControlPlaneError, EngineError) as error:
        raise ToolError(f"{error.code}: {error.message}") from error

    access = access_result.access
    if access.document_key != engine_result.document_access_key:
        raise ToolError(
            "DOCUMENT_ACCESS_FAILED: the control plane returned misaligned document authorization."
        )
    return GetDocumentsOutput(
        trial_id=engine_result.trial_id,
        document_name=engine_result.document_name,
        document_type=engine_result.document_type,
        part=engine_result.part,
        text=engine_result.text,
        next_part=engine_result.next_part,
        analysis_allowance=AnalysisAllowance(
            limit=access.limit,
            used=access.used,
            remaining=access.remaining,
        ),
    )


@mcp.tool(
    title="Extract trial variables",
    meta=OAUTH_TOOL_META,
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
@track_tool_call("extract_variables")
async def extract_variables(
    analysis_id: Annotated[
        str,
        Field(
            min_length=20,
            max_length=128,
            description="Active 60-minute analysis ID returned by start_analysis.",
        ),
    ],
    trial_id: Annotated[
        str,
        Field(
            pattern=r"^\d{4}-\d{6}-\d{2}-\d{2}$",
            description="One EU trial number with a current approved Trial Profile.",
        ),
    ],
    variables: Annotated[
        list[ExtractionVariable],
        Field(
            min_length=1,
            max_length=MAX_VARIABLES_PER_CALL,
            description=(
                "One to 20 uniquely named variables. Each variable has a snake_case name, a precise "
                "instruction and a requested value type. Missing values are returned as null."
            ),
        ),
    ],
) -> ExtractVariablesOutput:
    """Extract up to 20 caller-defined values from one trial in one Terra worker call.

    The Engine supplies the complete current approved Trial Profile plus the complete extracted text
    of the single protocol named in filtering_variables.available_extracted_documents.protocol when
    available. Terra uses the profile as the primary
    source and the protocol to complete or correct protocol-defined details. When the profile has no
    extracted protocol, extraction uses the profile alone.

    Every requested variable is returned under its exact name. A source that does not establish the
    answer produces null. The result intentionally contains no status, explanation, evidence, document
    name or page metadata. The worker uses no external knowledge and performs no download, OCR or
    document extraction.

    Exactly one model request is made per tool invocation, with no automatic model retry, to keep latency
    bounded. Exact caller retries reuse the stable trial+variables allowance key.
    """
    try:
        normalized_variables = normalize_variables(variables)
    except ValueError as error:
        raise ToolError(f"INVALID_VARIABLES: {error}") from error

    key = extraction_key(trial_id, normalized_variables)
    control = control_plane_client()
    try:
        source = await engine_client().extraction_source(trial_id)
        reservation = await control.authorize_extraction(
            analysis_id,
            key,
            len(normalized_variables),
            "reserve",
        )
    except (ControlPlaneError, EngineError) as error:
        raise ToolError(f"{error.code}: {error.message}") from error

    if reservation.access.extraction_key != key:
        raise ToolError(
            "EXTRACTION_ACCESS_FAILED: the control plane returned misaligned extraction authorization."
        )

    set_worker_model(reservation.access.worker_model)

    try:
        values = await TerraExtractor(settings).extract(
            trial_id=trial_id,
            profile=source.profile,
            protocol_text=source.protocol_text,
            variables=normalized_variables,
            model=reservation.access.worker_model,
        )
    except ExtractorError as error:
        try:
            await control.authorize_extraction(
                analysis_id, key, len(normalized_variables), "release"
            )
        except ControlPlaneError:
            pass
        raise ToolError(f"{error.code}: {error.message}") from error
    except Exception:
        try:
            await control.authorize_extraction(
                analysis_id, key, len(normalized_variables), "release"
            )
        except ControlPlaneError:
            pass
        raise

    try:
        committed = await control.authorize_extraction(
            analysis_id, key, len(normalized_variables), "commit"
        )
    except ControlPlaneError as error:
        raise ToolError(f"{error.code}: {error.message}") from error

    return ExtractVariablesOutput(
        trial_id=trial_id,
        values=values,
        analysis_allowance=AnalysisAllowance(
            limit=committed.access.limit,
            used=committed.access.used,
            remaining=committed.access.remaining,
        ),
    )


@mcp.custom_route("/", methods=["GET"])
async def documentation(_request: Request) -> Response:
    return HTMLResponse(
        DOCS_HTML,
        headers={
            "Cache-Control": "public, max-age=300",
            "Content-Security-Policy": (
                "default-src 'self'; img-src 'self' https://intel.trialagents.com data:; "
                "style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; "
                "base-uri 'self'; frame-ancestors 'none'; form-action 'none'"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "X-Content-Type-Options": "nosniff",
        },
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> Response:
    engine_status = "http_compatibility"
    if settings.engine_source == "database":
        try:
            reader = engine_client()
            assert isinstance(reader, DatabaseEngineClient)
            await reader.healthcheck()
            engine_status = "read_only_database_ok"
        except (EngineError, RuntimeError):
            return JSONResponse(
                {
                    "status": "degraded",
                    "service": "intel-mcp",
                    "engine_source": "database",
                    "engine": "unavailable",
                    "classifier_configured": bool(settings.openai_api_key),
                    "extractor_configured": bool(settings.openai_api_key),
                },
                status_code=503,
            )
    return JSONResponse(
        {
            "status": "ok",
            "service": "intel-mcp",
            "engine_source": settings.engine_source,
            "engine": engine_status,
            "classifier_configured": bool(settings.openai_api_key),
            "extractor_configured": bool(settings.openai_api_key),
            "report_planner_configured": bool(
                settings.openai_api_key and settings.report_plan_service_token
            ),
        }
    )


def _report_plan_authorized(request: Request) -> bool:
    authorization = request.headers.get("authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    configured = settings.report_plan_service_token
    return bool(
        separator
        and scheme.casefold() == "bearer"
        and configured
        and secrets.compare_digest(supplied.strip(), configured)
    )


@mcp.custom_route("/internal/report-plan", methods=["POST"])
async def report_plan(request: Request) -> Response:
    if not _report_plan_authorized(request):
        return JSONResponse({"error": "Unauthorized."}, status_code=401)
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 80_000:
        return JSONResponse({"error": "Report-plan request is too large."}, status_code=413)
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "A valid JSON request is required."}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "A valid JSON request is required."}, status_code=400)
    context = body.get("context")
    insights = body.get("insights")
    revision = body.get("revision")
    current_plan = body.get("currentPlan")
    if not isinstance(context, str) or not isinstance(insights, str):
        return JSONResponse({"error": "Trial context and requested insights are required."}, status_code=400)
    if revision is not None and not isinstance(revision, str):
        return JSONResponse({"error": "The revision request must be text."}, status_code=400)
    if current_plan is not None and not isinstance(current_plan, dict):
        return JSONResponse({"error": "The current report plan is invalid."}, status_code=400)
    try:
        plan = await SolReportPlanner(settings).generate(
            context=context,
            insights=insights,
            revision=revision,
            current_plan=current_plan,
        )
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    except ReportPlanError as error:
        LOGGER.warning("Sol report planning failed: %s", error.code)
        status_code = 503 if error.retryable or error.code == "REPORT_PLAN_NOT_CONFIGURED" else 422
        return JSONResponse(
            {"error": "Sol could not prepare the report plan. Please try again."},
            status_code=status_code,
        )
    return JSONResponse({"plan": plan.model_dump(), "source": "sol"})


def protected_resource_metadata() -> JSONResponse:
    return JSONResponse(
        {
            "resource": settings.mcp_public_resource_url,
            "authorization_servers": [settings.oauth_authorization_server_url],
            "scopes_supported": [OAUTH_SCOPE],
            "bearer_methods_supported": ["header"],
            "resource_documentation": settings.mcp_public_resource_url.removesuffix("/mcp") + "/",
        },
        headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"},
    )


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def oauth_protected_resource(_request: Request) -> Response:
    return protected_resource_metadata()


@mcp.custom_route("/.well-known/oauth-protected-resource/mcp", methods=["GET"])
async def oauth_protected_resource_path(_request: Request) -> Response:
    return protected_resource_metadata()


transport_security = TransportSecuritySettings(allowed_hosts=list(settings.allowed_hosts))


class MCPServiceAuthMiddleware:
    """Accept the internal service bearer or a scoped TrialAgents user OAuth token."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        scheme, separator, token = authorization.partition(" ")
        internal = (
            bool(separator)
            and scheme.lower() == "bearer"
            and bool(settings.mcp_inbound_service_token)
            and secrets.compare_digest(token, settings.mcp_inbound_service_token)
        )
        if internal:
            await self.app(scope, receive, send)
            return

        if not separator or scheme.lower() != "bearer" or not token:
            response = JSONResponse(
                {"error": {"code": "UNAUTHORIZED", "message": "Connect a TrialAgents account to use this MCP server."}},
                status_code=401,
                headers={"WWW-Authenticate": self._challenge()},
            )
            await response(scope, receive, send)
            return

        try:
            token_info = await control_plane_client().introspect_access_token(token)
        except (ControlPlaneError, RuntimeError):
            response = JSONResponse(
                {"error": {"code": "OAUTH_VALIDATION_UNAVAILABLE", "message": "OAuth validation is temporarily unavailable."}},
                status_code=503,
            )
            await response(scope, receive, send)
            return

        scopes = set(str(token_info.get("scope", "")).split())
        subject = token_info.get("sub")
        valid_oauth = (
            token_info.get("active") is True
            and isinstance(subject, str)
            and bool(subject)
            and token_info.get("resource") == settings.mcp_public_resource_url
            and OAUTH_SCOPE in scopes
        )
        if not valid_oauth:
            response = JSONResponse(
                {"error": {"code": "INVALID_OAUTH_TOKEN", "message": "The OAuth access token is invalid, expired, revoked or not issued for this MCP server."}},
                status_code=401,
                headers={"WWW-Authenticate": f'{self._challenge()}, error="invalid_token"'},
            )
            await response(scope, receive, send)
            return

        context_token = set_oauth_subject(subject)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_oauth_subject(context_token)

    @staticmethod
    def _challenge() -> str:
        origin = settings.mcp_public_resource_url.removesuffix("/mcp")
        return f'Bearer resource_metadata="{origin}/.well-known/oauth-protected-resource", scope="{OAUTH_SCOPE}"'


app = MCPServiceAuthMiddleware(mcp.streamable_http_app(transport_security=transport_security))


def main() -> None:
    uvicorn.run("intel_mcp.server:app", host="0.0.0.0", port=settings.port, proxy_headers=True)