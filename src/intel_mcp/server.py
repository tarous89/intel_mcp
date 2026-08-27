from __future__ import annotations

import secrets
from typing import Annotated

import uvicorn
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from intel_mcp.classification import (
    ClassifierError,
    ClassifyTrialsOutput,
    aggregate_trial_result,
    classification_key,
    classify_profile_items,
    validate_criteria,
)
from intel_mcp.config import Settings
from intel_mcp.control_plane import ControlPlaneClient, ControlPlaneError
from intel_mcp.engine import EngineClient, EngineError
from intel_mcp.models import (
    AnalysisLimits,
    FilterBudget,
    FilterTrialsOutput,
    StartAnalysisOutput,
    TrialFilters,
    TrialSort,
)

settings = Settings.from_environment()
mcp = MCPServer(
    "TrialAgents Intel MCP",
    instructions=(
        "Use start_analysis once after the Intel Agent app has created an approved report run. "
        "Pass the returned analysis_id to every later Intel tool."
    ),
)


def control_plane_client() -> ControlPlaneClient:
    return ControlPlaneClient(settings)


def engine_client() -> EngineClient:
    return EngineClient(settings)


@mcp.tool(
    title="Start Intel analysis",
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
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
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
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
    cursor: Annotated[
        str | None,
        Field(
            default=None,
            max_length=2000,
            description="Opaque cursor returned by the immediately preceding compatible filter call.",
        ),
    ] = None,
) -> FilterTrialsOutput:
    """Deterministically shortlist approved structured Trial Profiles.

    This tool queries only documented structured columns. It does not search the complete profile,
    run semantic search, classify trials, retrieve full profiles/documents, extract variables, or
    write a report. Sponsor-name matching is a shortlist aid: the CTIS source can sometimes identify
    a subsidy/funding source or omit part of the complete legal entity name.

    Results are validated and metered against the app-owned analysis lease. Light analyses may see
    at most 100 unique filtered trial IDs and Max analyses at most 1,000; retries and revisions do not
    consume the same trial ID twice. Continue only with next_cursor returned by this tool.
    """
    try:
        engine_result = await engine_client().filter_trials(
            filters=filters,
            sort=sort,
            limit=limit,
            cursor=cursor,
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
    warnings = list(engine_result.warnings)
    allowance_removed_results = len(data) != len(engine_result.data)
    if allowance_removed_results:
        warnings.append(
            "The analysis filtered-trial allowance was reached; additional new trial IDs were not returned."
        )

    has_more = engine_result.has_more and not access.exhausted and not allowance_removed_results
    return FilterTrialsOutput(
        data=data,
        applied_filters=engine_result.applied_filters,
        coverage=engine_result.coverage,
        warnings=warnings,
        returned=len(data),
        requested_limit=limit,
        applied_limit=engine_result.applied_limit,
        has_more=has_more,
        next_cursor=engine_result.next_cursor if has_more else None,
        analysis_budget=FilterBudget(
            limit=access.limit,
            used=access.used,
            remaining=access.remaining,
            exhausted=access.exhausted,
        ),
        schema_version=engine_result.schema_version,
    )


@mcp.tool(
    title="Classify approved clinical trials",
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
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

    The tool uses approved Trial Profiles only, does not inspect protocols or other documents, and does not
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

    try:
        worker_results = await classify_profile_items(
            settings,
            profile_result.data,
            inclusion,
            exclusion,
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
        await control.authorize_classifications(analysis_id, keys, "commit")
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
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> Response:
    return JSONResponse(
        {
            "status": "ok",
            "service": "intel-mcp",
            "classifier_configured": bool(settings.openai_api_key),
        }
    )


transport_security = TransportSecuritySettings(allowed_hosts=list(settings.allowed_hosts))


class MCPServiceAuthMiddleware:
    """Require the internal service bearer on every MCP protocol request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        try:
            settings.validate_inbound_auth()
        except RuntimeError:
            response = JSONResponse(
                {"error": {"code": "MCP_AUTH_NOT_CONFIGURED", "message": "MCP authentication is not configured."}},
                status_code=503,
            )
            await response(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        scheme, separator, token = authorization.partition(" ")
        valid = (
            bool(separator)
            and scheme.lower() == "bearer"
            and secrets.compare_digest(token, settings.mcp_inbound_service_token)
        )
        if not valid:
            response = JSONResponse(
                {"error": {"code": "UNAUTHORIZED", "message": "A valid MCP service credential is required."}},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


app = MCPServiceAuthMiddleware(mcp.streamable_http_app(transport_security=transport_security))


def main() -> None:
    uvicorn.run("intel_mcp.server:app", host="0.0.0.0", port=settings.port, proxy_headers=True)
