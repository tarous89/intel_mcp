"""A report-bound MCP surface. Discovery and dispatch enforce three read tools."""
from __future__ import annotations

import json
import re
import secrets

import httpx
from starlette.responses import JSONResponse, Response

from intel_mcp.control_plane import ControlPlaneClient
from intel_mcp.engine_database import DatabaseEngineClient
from intel_mcp.max_agent_config import MaxAgentConfig
from intel_mcp.max_agent_evidence import EvidenceStore, digest, freeze_document, freeze_profile_batch, load_profiles
from intel_mcp.max_agent_session import TOOLS, scoped_token
from intel_mcp.models import TrialFilters, TrialSort
from intel_mcp.report_artifacts import ArtifactStore, UUID


class MaxControl:
    def __init__(self, settings):
        self.settings = settings

    async def call(self, action, **payload):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self.settings.app_control_url + "/api/internal/max-agent",
                headers={"Authorization": "Bearer " + self.settings.app_service_token},
                json={"action": action, **payload})
            response.raise_for_status()
            return response.json()


def tool_definitions():
    def tool(name, description, properties, required=()):
        return {"name": name, "description": description, "inputSchema": {
            "type": "object", "properties": properties, "required": list(required), "additionalProperties": False},
            "annotations": {"readOnlyHint": True, "destructiveHint": False}}
    return [
        tool("filter_trials", "Search saved profiles by text. Live structured filters are allowed only for an explicit request for new evidence.", {
            "query": {"type": "string", "maxLength": 500}, "live": {"type": "boolean", "default": False},
            "filters": {"type": "object"}, "offset": {"type": "integer", "minimum": 0, "maximum": 20000}}),
        tool("get_profiles", "Get complete frozen profiles. Additional IDs must first be discovered for this report.", {
            "trial_ids": {"type": "array", "minItems": 1, "maxItems": 10, "uniqueItems": True,
                          "items": {"type": "string", "pattern": r"^\d{4}-\d{6}-\d{2}-\d{2}$"}}}, ["trial_ids"]),
        tool("get_documents", "Read an existing extracted-text part by its exact profile-listed name. No PDF retrieval or OCR.", {
            "trial_id": {"type": "string", "pattern": r"^\d{4}-\d{6}-\d{2}-\d{2}$"},
            "document_name": {"type": "string", "minLength": 1, "maxLength": 1000},
            "part": {"type": "integer", "minimum": 1, "maximum": 10000}}, ["trial_id", "document_name", "part"]),
    ]


def permits_new_evidence(job):
    if job["base_version"] == 0:
        return True
    text = job.get("request_text", "")
    if re.search(r"\b(do not|don't|without|no|never)\b.{0,50}\b(new|latest|current|refresh|update|additional)\b", text, re.I):
        return False
    return bool(re.search(r"\b(new|latest|current|recent|additional|updated)\s+(trials?|evidence|data|studies|profiles?)\b|\b(refresh|update|expand)\s+(?:the\s+)?(evidence|cohort|dataset|trial\s+list)\b",
                          text, re.I))


class ReportRetrieval:
    def __init__(self, settings, *, control=None, evidence=None, engine=None, allowances=None, config=None):
        self.control = control or MaxControl(settings)
        self.evidence = evidence or EvidenceStore(ArtifactStore(settings))
        self.engine = engine or DatabaseEngineClient(settings, all_profiles=True)
        self.allowances = allowances or ControlPlaneClient(settings)
        self.config = config or MaxAgentConfig.from_environment()

    async def call(self, run_id, name, arguments):
        if name not in TOOLS:
            raise PermissionError("Tool is not available to the Max analyst")
        import jsonschema
        schema = next(t["inputSchema"] for t in tool_definitions() if t["name"] == name)
        jsonschema.validate(arguments, schema)
        for attempt in range(4):
            access = await self.control.call("active", reportRunId=run_id)
            job, analysis_id = access["job"], access["analysisId"]
            old_sha = job["checkpoint"]["evidenceSha"]
            manifest = await self.evidence.get(run_id, old_sha)
            if manifest.get("reportRunId") != run_id:
                raise PermissionError("Cross-report evidence access")
            profiles = await load_profiles(self.evidence, manifest)
            changed = manifest
            if name == "filter_trials":
                offset = arguments.get("offset", 0)
                query = arguments.get("query", "").casefold()
                if arguments.get("live"):
                    if not permits_new_evidence(job):
                        raise PermissionError("This revision reuses saved evidence")
                    filters = TrialFilters.model_validate(arguments.get("filters", {}))
                    if query:
                        data = filters.model_dump(exclude_none=True)
                        data["trial_title"] = {"operator": "contains", "value": query}
                        filters = TrialFilters.model_validate(data)
                    result = await self.engine.filter_trials(filters=filters, sort=TrialSort(field="eu_number", direction="asc"), limit=100, offset=offset)
                    found = [p.model_dump(mode="json") for p in result.data]
                    authorization = await self.allowances.authorize_filter_results(analysis_id, [p["eu_number"] for p in found])
                    allowed = set(authorization.access.allowed_trial_ids)
                    found = [p for p in found if p["eu_number"] in allowed]
                    discovered = dict(manifest.get("discovered", {}))
                    discovered.update({p["eu_number"]: p for p in found})
                    changed = {**manifest, "discovered": discovered}
                    output = {"data": found, "totalMatches": result.counts.total_matches, "source": "live"}
                else:
                    if arguments.get("filters"):
                        raise ValueError("Use query for frozen profiles; structured filters require live evidence access")
                    found = [p for p in profiles.values() if not query or query in json.dumps(p, ensure_ascii=False).casefold()]
                    output = {"data": [{"eu_number": p["eu_number"], "profileHash": manifest["profiles"][p["eu_number"]]["profileHash"]} for p in found[offset:offset + 100]],
                              "totalMatches": len(found), "source": "snapshot"}
            elif name == "get_profiles":
                ids = arguments["trial_ids"]
                missing = [tid for tid in ids if tid not in profiles]
                if missing:
                    if not permits_new_evidence(job) or any(tid not in manifest.get("discovered", {}) for tid in missing):
                        raise PermissionError("Trial has not been discovered for this report")
                    if len(profiles) + len(missing) > self.config.trial_limit:
                        raise PermissionError("Report trial allowance exceeded")
                    allowed = await self.allowances.authorize_profiles(analysis_id, missing)
                    if set(allowed.access.allowed_trial_ids) != set(missing):
                        raise PermissionError("Report profile allowance exceeded")
                    result = await self.engine.get_profiles(missing)
                    records = [p.model_dump(mode="json") for p in result.data]
                    changed = await freeze_profile_batch(self.evidence, manifest, records)
                    profiles.update({p["eu_number"]: p for p in records})
                output = {"profiles": [profiles[tid] for tid in ids if tid in profiles], "unavailable_trial_ids": [tid for tid in ids if tid not in profiles]}
            else:
                tid, filename, part = arguments["trial_id"], arguments["document_name"], arguments["part"]
                if tid not in profiles:
                    raise PermissionError("Document is outside the report cohort")
                inventory = profiles[tid]["profile"].get("filtering_variables", {}).get("available_extracted_documents", {})
                if not any(filename in names for names in inventory.values() if isinstance(names, list)):
                    raise PermissionError("Use an exact saved-profile document name")
                key = digest([tid, filename, part])
                cached = manifest["documents"].get(key)
                if cached:
                    saved = await self.evidence.get(run_id, cached["sha"])
                    output = saved["document"]
                    if saved.get("reportRunId") != run_id or digest(output) != cached["contentHash"]:
                        raise ValueError("Document evidence checksum mismatch")
                else:
                    documents = list(manifest["documents"].values())
                    distinct = {(d["trialId"], d["name"]) for d in documents}
                    if (tid, filename) not in distinct and len(distinct) >= self.config.document_limit:
                        raise PermissionError("Report document allowance exceeded")
                    result = await self.engine.get_document(trial_id=tid, document_name=filename, part=part)
                    output = result.model_dump(mode="json")
                    if (output["trial_id"], output["part"]) != (tid, part):
                        raise ValueError("Document identity mismatch")
                    if len(output["text"]) + sum(d["characters"] for d in documents) > self.config.document_characters:
                        raise PermissionError("Report document-text allowance exceeded")
                    await self.allowances.authorize_document(analysis_id, output["document_access_key"])
                    output["document_name"] = filename
                    changed = await freeze_document(self.evidence, manifest, output)
            if changed != manifest:
                new_sha = await self.evidence.put(run_id, changed)
                try:
                    await self.control.call("evidence", reportRunId=run_id, jobId=job["id"], expectedSha=old_sha, evidenceSha=new_sha)
                except httpx.HTTPStatusError as error:
                    if error.response.status_code == 409 and attempt < 3:
                        continue
                    raise
            return output
        raise RuntimeError("Concurrent evidence update; retry the read")


def register_max_tools(mcp, settings):
    retrieval = ReportRetrieval(settings)

    @mcp.custom_route("/max-agent/mcp/{run_id}", methods=["POST", "GET", "DELETE"])
    async def endpoint(request):
        run_id = request.path_params["run_id"]
        if not UUID.fullmatch(run_id):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
        if not settings.app_service_token or not secrets.compare_digest(supplied, scoped_token(settings.app_service_token, run_id)):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        try:
            await retrieval.control.call("active", reportRunId=run_id)
        except Exception:
            return JSONResponse({"error": "No active report lease"}, status_code=403)
        if request.method != "POST":
            return Response(status_code=405)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 100000:
                return Response(status_code=413)
        try:
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError()
        except ValueError:
            return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid JSON"}})
        rid, method = body.get("id"), body.get("method")
        if method == "notifications/initialized":
            return Response(status_code=202)
        try:
            if method == "initialize":
                requested = body.get("params", {}).get("protocolVersion")
                version = requested if requested in {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"} else "2025-06-18"
                result = {"protocolVersion": version, "capabilities": {"tools": {}}, "serverInfo": {"name": "TrialAgents Max Evidence", "version": "1"}}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": tool_definitions()}
            elif method == "tools/call":
                params = body.get("params", {})
                if params.get("name") not in TOOLS:
                    raise PermissionError("Tool is not available")
                value = await retrieval.call(run_id, params["name"], params.get("arguments", {}))
                result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}], "isError": False}
            else:
                raise PermissionError("Method is not available")
            return JSONResponse({"jsonrpc": "2.0", "id": rid, "result": result})
        except (PermissionError, ValueError) as error:
            return JSONResponse({"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": str(error)}})
        except Exception:
            return JSONResponse({"jsonrpc": "2.0", "id": rid, "error": {"code": -32603, "message": "Evidence read temporarily unavailable"}})
