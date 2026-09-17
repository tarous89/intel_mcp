"""Durable two-stage Max worker. App claims fence all publication mutations.

Run as a supervised process: python -m intel_mcp.max_agent_execution.
Each iteration resumes a checkpoint; no work depends on a web-request lifetime.
"""
from __future__ import annotations

import asyncio
import gzip
import hashlib
import html
import json
import logging
import re
import tempfile
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path

import httpx

from intel_mcp.config import Settings
from intel_mcp.control_plane import ControlPlaneClient
from intel_mcp.engine_database import DatabaseEngineClient
from intel_mcp.max_agent_config import MaxAgentConfig
from intel_mcp.max_agent_evidence import EvidenceStore, canonical, digest, freeze_profile_batch, load_profiles, new_manifest, now, select_candidates
from intel_mcp.max_agent_exports import optional_pdf, subprocess_export
from intel_mcp.max_agent_instructions import INSTRUCTIONS, TEMPLATE, VERSION
from intel_mcp.max_agent_output import TEMPLATE_VERSION, render_html, review
from intel_mcp.max_agent_session import ManagedAgent, ManagedAgentError
from intel_mcp.max_agent_pdf import retry_pdf
from intel_mcp.max_agent_tools import MaxControl
from intel_mcp.max_report_execution import _execution_plan, _trial_filters
from intel_mcp.models import TrialSort
from intel_mcp.report_artifacts import ArtifactStore

LOGGER = logging.getLogger("intel_mcp.max_agent")


class MaxAgentWorker:
    def __init__(self, settings, *, control=None, agent=None, engine=None, evidence=None, allowances=None):
        self.config = MaxAgentConfig.from_environment()
        self.settings = settings
        self.control = control or MaxControl(settings)
        self.agent = agent or ManagedAgent(settings, self.config)
        self.engine = engine or DatabaseEngineClient(settings, all_profiles=True)
        self.artifacts = ArtifactStore(settings)
        self.evidence = evidence or EvidenceStore(self.artifacts)
        self.allowances = allowances or ControlPlaneClient(settings)

    async def checkpoint(self, job, status, *, release=False, **values):
        await self.control.call("checkpoint", reportRunId=job["report_run_id"], jobId=job["id"],
            claimToken=job["claim_token"], status=status, release=release, **values)
        job["checkpoint"].update(values.get("checkpoint", {}))
        if "sessionId" in values:
            job["session_id"] = values["sessionId"]
        if values.get("turnId"):
            job["turn_id"] = values["turnId"]
        job["status"] = status

    async def prepare(self, job, run, lease):
        run_id, cp = job["report_run_id"], job["checkpoint"]
        plan = run["plan"]
        cohorts, _ = _execution_plan(plan)
        if not cp.get("evidenceSha"):
            # Discovery itself is checkpointed page by page, before profile reads.
            selection = await self.evidence.get(run_id, cp["selectionSha"]) if cp.get("selectionSha") else {
                "criteria": [c["discoveryFilter"] for c in cohorts], "pools": [[] for _ in cohorts],
                "groupIndex": 0, "offset": 0, "complete": False, "trace": [],
                "rule": "round-robin approved seeds; stable SHA256 order within each stratum",
            }
            if not selection["complete"]:
                index, offset = selection["groupIndex"], selection["offset"]
                result = await self.engine.filter_trials(filters=_trial_filters(selection["criteria"][index]),
                    sort=TrialSort(field="eu_number", direction="asc"), limit=100, offset=offset)
                ids = [row.eu_number for row in result.data]
                selection["pools"][index] = list(dict.fromkeys(selection["pools"][index] + ids))
                next_offset = offset + len(ids)
                done = not ids or next_offset >= min(result.counts.total_matches, self.config.discovery_limit)
                if done:
                    selection["trace"].append({"group": index + 1, "totalMatches": result.counts.total_matches,
                        "retrieved": next_offset, "bounded": result.counts.total_matches > self.config.discovery_limit})
                    selection["groupIndex"], selection["offset"] = index + 1, 0
                    selection["complete"] = index + 1 == len(cohorts)
                else:
                    selection["offset"] = next_offset
                selection_sha = await self.evidence.put(run_id, selection)
                await self.checkpoint(job, "preparing", release=True, checkpoint={"selectionSha": selection_sha},
                    activity="Preparing evidence: discovering candidates")
                return
            ids = select_candidates(selection["pools"], self.config.trial_limit, digest(plan))
            selection["selectedIds"] = ids
            manifest = new_manifest(run_id, plan, {"context": run["context"], "insights": run["insights"]}, selection)
            manifest["unavailableIds"] = []
            sha = await self.evidence.put(run_id, manifest)
            await self.checkpoint(job, "preparing", checkpoint={"evidenceSha": sha, "evidenceVersion": 2})
        manifest = await self.evidence.get(run_id, cp["evidenceSha"])
        missing = [tid for tid in manifest["selection"]["selectedIds"]
                   if tid not in manifest["profiles"] and tid not in manifest.get("unavailableIds", [])]
        if missing:
            ids = missing[:10]
            filtered = await self.allowances.authorize_filter_results(lease["analysisId"], ids)
            allowed = await self.allowances.authorize_profiles(lease["analysisId"], ids)
            if set(filtered.access.allowed_trial_ids) != set(ids) or set(allowed.access.allowed_trial_ids) != set(ids):
                raise ManagedAgentError("EVIDENCE_ALLOWANCE_EXCEEDED")
            result = await self.engine.get_profiles(ids)
            manifest = await freeze_profile_batch(self.evidence, manifest, [p.model_dump(mode="json") for p in result.data])
            manifest["unavailableIds"] = list(dict.fromkeys(manifest.get("unavailableIds", []) + result.unavailable_trial_ids))
            sha = await self.evidence.put(run_id, manifest)
            await self.checkpoint(job, "preparing", release=True, checkpoint={"evidenceSha": sha},
                activity=f"Preparing evidence: {len(manifest['profiles'])} profiles saved")
            return
        await self.checkpoint(job, "analyzing", release=True,
            activity="Analyzing the approved topics", checkpoint={"startedAt": cp.get("startedAt") or now()})

    async def package(self, job):
        manifest = await self.evidence.get(job["report_run_id"], job["checkpoint"]["evidenceSha"])
        profiles = await load_profiles(self.evidence, manifest)
        documents = {}
        for key, ref in manifest["documents"].items():
            record = await self.evidence.get(job["report_run_id"], ref["sha"])
            if record["reportRunId"] != job["report_run_id"] or digest(record["document"]) != ref["contentHash"]:
                raise ValueError("Invalid document evidence")
            documents[key] = record["document"]
        return manifest, profiles, documents

    async def session(self, job):
        cp, run_id = job["checkpoint"], job["report_run_id"]
        if job.get("session_id"):
            return
        intent = f"{job['id']}:session:{cp.get('recoveryCount', 0)}"
        await self.checkpoint(job, "analyzing", checkpoint={"sessionIntent": intent, "model": self.config.model})
        found = await self.agent.find_session(intent)
        if not found:
            await self.agent.preflight()
            manifest, profiles, documents = await self.package(job)
            package = {"manifest": manifest, "profiles": profiles, "documents": documents}
            if cp.get("workSha"):
                package["previousWork"] = await self.evidence.get(run_id, cp["workSha"])
            files = {"evidence.json.gz": gzip.compress(canonical(package), mtime=0),
                "contract.json": canonical({"instructionsVersion": VERSION, "templateVersion": TEMPLATE_VERSION,
                    "reportRunId": run_id, "baseVersion": job["base_version"]}),
                "template.html": TEMPLATE.encode(),
                "max_calculations.py": Path(__file__).with_name("max_agent_output.py").read_bytes()}
            refs, inline_bytes = {}, sum(map(len, files.values()))
            uploaded = dict(cp.get("inputFiles", {}))
            for name, data in sorted(files.items(), key=lambda item: -len(item[1])):
                if len(data) <= 5 * 1024 * 1024 and inline_bytes <= 10 * 1024 * 1024:
                    continue
                checksum = hashlib.sha256(data).hexdigest()
                previous = uploaded.get(name, {})
                if previous.get("sha") != checksum:
                    file_id = await self.agent.upload_input(name, data)
                    uploaded[name] = {"id": file_id, "sha": checksum}
                    await self.checkpoint(job, "analyzing", checkpoint={"inputFiles": uploaded})
                refs[name] = uploaded[name]["id"]
                inline_bytes -= len(data)
            found = await self.agent.create_idle(run_id, intent, INSTRUCTIONS, files, refs)
        await self.checkpoint(job, "analyzing", sessionId=found["id"])

    async def analyze(self, job):
        cp = job["checkpoint"]
        await self.session(job)
        try:
            session, turns = await self.agent.inspect(job["session_id"])
        except ManagedAgentError as error:
            if error.code != "AGENT_SESSION_NOT_FOUND":
                raise
            session, turns = {"status": "failed"}, []
        environment_lost = any(a.get("type") == "environment_connection" for a in session.get("required_actions", []))
        if session.get("status") == "failed" or environment_lost:
            # Replacement is permitted only after a terminal state or confirmed
            # missing environment, never after an ambiguous network failure.
            if cp.get("recoveryCount", 0) >= 2:
                raise ManagedAgentError("AGENT_SESSION_RECOVERY_EXHAUSTED")
            if environment_lost:
                await self.agent.cancel(job["session_id"])
            await self.checkpoint(job, "analyzing", release=True, sessionId="",
                checkpoint={"recoveryCount": cp.get("recoveryCount", 0) + 1, "turnIntent": ""},
                activity="Restoring the analyst from saved evidence and work")
            return
        if not cp.get("turnIntent"):
            previous = turns[0]["id"] if turns else ""
            count = int(cp.get("turnCount", 0)) + 1
            if count > self.config.max_turns:
                raise ManagedAgentError("AGENT_TURN_BUDGET_EXCEEDED")
            await self.checkpoint(job, "analyzing", checkpoint={"turnIntent": f"{job['id']}:turn:{count}",
                "previousTurnId": previous, "turnCount": count})
        # The API returns newest first. Never use any older turn as this job's
        # result, including when recovery brings back more than one prior turn.
        current = turns[0] if turns and turns[0]["id"] != cp["previousTurnId"] else None
        if not current:
            request = job.get("request_text") or "Prepare the initial report for the approved brief and plan."
            request = (f"Report job {job['id']}; published base version {job['base_version']}. "
                       "Only this request defines the current task. Preserve the approved plan and frozen evidence.\n" + request)
            if cp.get("correctionCount"):
                saved = await self.evidence.get(job["report_run_id"], cp["workSha"])
                request = "Correct these targeted validation issues, keeping valid material: " + json.dumps(saved.get("issues", []))
            await self.agent.send(job["session_id"], request, cp["turnIntent"])
            await self.checkpoint(job, "analyzing", release=True, delaySeconds=15,
                activity="Analyzing the approved topics")
            return
        if current["status"] in {"failed", "cancelled"}:
            raise ManagedAgentError("AGENT_TURN_FAILED")
        if current["status"] != "completed":
            await self.checkpoint(job, "analyzing", release=True, delaySeconds=15, turnId=current["id"],
                activity="Analyzing the approved topics")
            return
        await self.checkpoint(job, "rendering", release=True, turnId=current["id"],
            checkpoint={"usage": current.get("usage"), "templateVersion": TEMPLATE_VERSION},
            activity="Preparing report: checking calculations and saving artifacts")

    async def publish(self, job):
        cp, run_id = job["checkpoint"], job["report_run_id"]
        manifest, profiles, documents = await self.package(job)
        with tempfile.TemporaryDirectory(prefix="max-agent-output-") as directory:
            root = Path(directory)
            artifacts = await self.agent.artifacts(job["session_id"], job["turn_id"])
            if sum(a["size_bytes"] for a in artifacts) > 64 * 1024 * 1024:
                raise ManagedAgentError("AGENT_OUTPUT_TOO_LARGE")
            saved = {}
            for index, artifact in enumerate(artifacts):
                name = Path(artifact["path"]).name
                if name in saved:
                    raise ValueError("Duplicate output filename")
                if not (name in {"work.json", "report.html"} or name.endswith((".py", ".json", ".csv", ".txt"))):
                    continue
                target = root / str(index)
                await self.agent.download(job["session_id"], artifact["id"], target)
                saved[name] = target.read_text(encoding="utf-8")
            try:
                work = json.loads(saved.get("work.json", "{}"))
            except (ValueError, TypeError):
                work = {}
            if not isinstance(work, dict):
                work = {}
            if work.get("kind") == "answer" and job["base_version"] > 0 and isinstance(work.get("answer"), str):
                work_sha = await self.evidence.put(run_id, {"work": work, "evidenceSha": cp["evidenceSha"],
                    "sessionId": job["session_id"], "turnId": job["turn_id"]})
                await self.checkpoint(job, "rendering", checkpoint={"workSha": work_sha})
                await self.control.call("publish", reportRunId=run_id, jobId=job["id"], claimToken=job["claim_token"],
                    answer=work["answer"], changeSummary="")
                return
            metrics, issues = review(work, profiles, documents, manifest["approvedPlan"])
            text = job.get("request_text", "")
            presentation_only = bool(re.search(r"\b(font|formatting|layout|colou?r|spacing|typography|title|heading)\b", text, re.I)) and not re.search(r"\b(analy[sz]|subgroup|evidence|trials?|data|recalculate)\b", text, re.I)
            if presentation_only and cp.get("baseWorkSha"):
                prior = await self.evidence.get(run_id, cp["baseWorkSha"])
                keys = ("facts", "membership", "metrics", "definitions")
                if digest({k: work.get(k) for k in keys}) != digest({k: prior["work"].get(k) for k in keys}):
                    issues.append({"code": "presentation_changed_data"})
            if not saved.get("report.html"):
                issues.append({"code": "missing_report_html"})
            payload = {"manifest": manifest, "profiles": profiles, "documents": documents,
                "work": work, "metrics": metrics, "issues": issues,
                "scripts": {k: v for k, v in saved.items() if k not in {"work.json", "report.html"}},
                "html": saved.get("report.html", ""), "sessionId": job["session_id"], "turnId": job["turn_id"]}
            work_sha = await self.evidence.put(run_id, payload)
            await self.checkpoint(job, "rendering", checkpoint={"workSha": work_sha})
            if issues and cp.get("correctionCount", 0) < 2 and cp.get("turnCount", 0) < self.config.max_turns:
                await self.checkpoint(job, "analyzing", release=True, checkpoint={
                    "correctionCount": cp.get("correctionCount", 0) + 1, "turnIntent": ""},
                    activity="Analyzing targeted evidence and calculation corrections")
                return
            title = str(work.get("title") or "Max report")[:200]
            raw = saved.get("report.html") or "<h1>Max report</h1><p>No supported report output was produced. The evidence is available in the dataset.</p>"
            # Unsupported facts/metrics must never survive as confident free prose.
            if any(i["code"] == "presentation_changed_data" for i in issues):
                # Preserve the completed version instead of publishing a data-changing format edit.
                raise ManagedAgentError("PRESENTATION_CHANGED_DATA")
            unsafe = any(i["code"] in {"unsupported_fact", "unsupported_metric", "invalid_membership"} for i in issues)
            if unsafe:
                raw = "<h1>" + html.escape(title) + "</h1><p>Some findings could not be verified. Only validated calculations are shown; source evidence and assessments remain in the dataset.</p>"
                raw += "".join('<div data-chart="' + html.escape(mid, quote=True) + '"></div>' for mid in metrics)
            rendered = render_html(raw, metrics, title)
            html_path = root / "report.html"
            html_path.write_text(rendered)
            html_sha = await self.artifacts.upload(run_id, html_path, "html")
            input_path, xlsx_path = root / "export.json", root / "dataset.xlsx"
            input_path.write_bytes(canonical(payload))
            await subprocess_export(input_path, xlsx_path)
            xlsx_sha = await self.artifacts.upload(run_id, xlsx_path, "xlsx")
            pdf_path = root / "report.pdf"
            pdf_sha = None
            try:
                if await optional_pdf(html_path, pdf_path):
                    pdf_sha = await self.artifacts.upload(run_id, pdf_path, "pdf")
            except Exception:
                LOGGER.warning("Optional PDF unavailable report=%s", run_id)
            report = {"version": 3, "format": "max_agent_html_v1", "tier": "max", "title": title,
                "executiveSummary": str(work.get("summary") or "")[:2000] if not unsafe else "",
                "htmlSha": html_sha, "xlsxSha": xlsx_sha, "pdfSha": pdf_sha,
                "workSha": work_sha, "evidenceSha": cp["evidenceSha"], "evidenceVersion": 2,
                "capturedAt": manifest["capturedAt"], "trialCount": len(profiles),
                "templateVersion": TEMPLATE_VERSION, "validationIssueCount": len(issues)}
            await self.control.call("publish", reportRunId=run_id, jobId=job["id"], claimToken=job["claim_token"],
                report=report, changeSummary=str(work.get("changeSummary") or "Report prepared")[:2000])

    async def once(self):
        claimed = await self.control.call("claim")
        if not claimed.get("job"):
            return await retry_pdf(self.control, self.artifacts)
        job, run = claimed["job"], claimed["run"]
        async def heartbeat():
            while True:
                await asyncio.sleep(40)
                await self.control.call("heartbeat", reportRunId=job["report_run_id"], jobId=job["id"], claimToken=job["claim_token"])
        pulse = asyncio.create_task(heartbeat())
        try:
            self.config.validate(self.settings)
            lease = await self.control.call("lease", reportRunId=job["report_run_id"], jobId=job["id"], claimToken=job["claim_token"])
            started = job["checkpoint"].get("startedAt")
            if started and (datetime.now(timezone.utc) - datetime.fromisoformat(started)).total_seconds() > self.config.max_minutes * 60:
                if job.get("session_id"):
                    await self.agent.cancel(job["session_id"])
                raise ManagedAgentError("AGENT_TIME_BUDGET_EXCEEDED")
            if job["status"] in {"queued", "preparing"}:
                await self.prepare(job, run, lease)
            elif job["status"] == "analyzing":
                await self.analyze(job)
            elif job["status"] == "rendering":
                await self.publish(job)
            LOGGER.info("Max checkpoint report=%s job=%s stage=%s", job["report_run_id"], job["id"], job["status"])
        except Exception as error:
            # A lost fencing claim is reconciled by the next worker; never fail it.
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 409:
                return True
            retryable = error.retryable if isinstance(error, ManagedAgentError) else isinstance(error, httpx.HTTPError) or getattr(error, "status_code", 0) >= 500
            code = getattr(error, "code", "MAX_AGENT_UNAVAILABLE")
            LOGGER.warning("Max checkpoint failed report=%s code=%s type=%s", job["report_run_id"], code, type(error).__name__)
            await self.control.call("retry" if retryable else "fail", reportRunId=job["report_run_id"],
                jobId=job["id"], claimToken=job["claim_token"], errorCode=code)
        finally:
            pulse.cancel()
            with suppress(asyncio.CancelledError, httpx.HTTPError):
                await pulse
        return True


async def serve():
    worker = MaxAgentWorker(Settings.from_environment())
    worker.config.validate(worker.settings)
    while True:
        try:
            busy = await worker.once()
            await asyncio.sleep(1 if busy else 5)
        except (httpx.HTTPError, OSError):
            LOGGER.warning("Max control unavailable; retaining durable jobs")
            await asyncio.sleep(15)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Managed Max worker and read-only account preflight")
    parser.add_argument("--preflight", action="store_true", help="Check configuration and Agents API access without starting a session")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.preflight:
        settings, config = Settings.from_environment(), MaxAgentConfig.from_environment()
        asyncio.run(ManagedAgent(settings, config).preflight())
        print("Managed Max account preflight passed; no session or model work started.")
    else:
        asyncio.run(serve())


if __name__ == "__main__":
    main()
