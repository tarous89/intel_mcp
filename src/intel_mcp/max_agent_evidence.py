"""Raw, immutable evidence checkpoints for the managed Max analyst.

No semantic work occurs here. Every batch is persisted before its manifest is
committed by the control plane; restart reuses those exact bytes.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from intel_mcp.report_artifacts import ArtifactStore

EVIDENCE_VERSION = 2
MAX_JSON_BYTES = 128 * 1024 * 1024


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceStore:
    def __init__(self, artifacts: ArtifactStore):
        self.artifacts = artifacts

    async def put(self, run_id: str, value: dict) -> str:
        raw = canonical(value)
        if len(raw) > MAX_JSON_BYTES:
            raise ValueError("Evidence exceeds configured storage bound")
        with tempfile.TemporaryDirectory(prefix="max-evidence-") as directory:
            path = Path(directory) / "evidence.json.gz"
            path.write_bytes(gzip.compress(raw, mtime=0))
            return await self.artifacts.upload(run_id, path, "json.gz")

    async def get(self, run_id: str, sha: str) -> dict:
        with tempfile.TemporaryDirectory(prefix="max-evidence-") as directory:
            path = Path(directory) / "evidence.json.gz"
            await self.artifacts.download(run_id, sha, "json.gz", path)
            with gzip.open(path, "rb") as source:
                raw = source.read(MAX_JSON_BYTES + 1)
            if len(raw) > MAX_JSON_BYTES:
                raise ValueError("Evidence exceeds configured storage bound")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("Invalid evidence object")
            return value


def select_candidates(pools: list[list[str]], limit: int, seed: str) -> list[str]:
    """Round-robin strata, deterministic hash order; never newest/first-page order."""
    ordered = [sorted(set(pool), key=lambda tid: hashlib.sha256(f"{seed}:{tid}".encode()).digest())
               for pool in pools]
    selected, seen = [], set()
    while any(ordered) and len(selected) < limit:
        for pool in ordered:
            while pool and pool[0] in seen:
                pool.pop(0)
            if pool and len(selected) < limit:
                trial_id = pool.pop(0)
                seen.add(trial_id)
                selected.append(trial_id)
    return selected


def new_manifest(run_id: str, plan: dict, brief: dict, selection: dict) -> dict:
    return {"version": EVIDENCE_VERSION, "reportRunId": run_id, "capturedAt": now(),
            "planHash": digest(plan), "approvedPlan": plan, "brief": brief,
            "selection": selection, "profiles": {}, "documents": {}}


async def freeze_profile_batch(store, manifest: dict, profiles: list[dict]) -> dict:
    """Return a new manifest only after the immutable batch is durably written."""
    run_id = manifest["reportRunId"]
    identities = [p["eu_number"] for p in profiles]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate profile identity")
    batch = {"version": EVIDENCE_VERSION, "reportRunId": run_id,
             "capturedAt": now(), "profiles": profiles}
    batch_sha = await store.put(run_id, batch)
    refs = dict(manifest["profiles"])
    for item in profiles:
        tid = item["eu_number"]
        # Already captured evidence is immutable, including on retries.
        refs.setdefault(tid, {"batchSha": batch_sha, "profileHash": digest(item),
                              "capturedAt": batch["capturedAt"],
                              "approvalStatus": item.get("approval_status"),
                              "schemaVersion": item.get("profile_schema_version")})
    return {**manifest, "profiles": refs}


async def load_profiles(store, manifest: dict) -> dict:
    profiles = {}
    for batch_sha in dict.fromkeys(ref["batchSha"] for ref in manifest["profiles"].values()):
        batch = await store.get(manifest["reportRunId"], batch_sha)
        if batch.get("reportRunId") != manifest["reportRunId"]:
            raise ValueError("Cross-report evidence")
        for item in batch["profiles"]:
            tid = item["eu_number"]
            ref = manifest["profiles"].get(tid)
            if ref and ref["batchSha"] == batch_sha:
                if digest(item) != ref["profileHash"]:
                    raise ValueError("Profile checksum mismatch")
                profiles[tid] = item
    if set(profiles) != set(manifest["profiles"]):
        raise ValueError("Incomplete saved profile batch")
    return profiles


async def freeze_document(store, manifest: dict, document: dict) -> dict:
    tid = document["trial_id"]
    if tid not in manifest["profiles"]:
        raise PermissionError("Document trial is outside the saved cohort")
    key = digest([tid, document["document_name"], document["part"]])
    if key in manifest["documents"]:
        return manifest
    record = {"version": EVIDENCE_VERSION, "reportRunId": manifest["reportRunId"],
              "capturedAt": now(), "document": document}
    sha = await store.put(manifest["reportRunId"], record)
    ref = {"sha": sha, "trialId": tid, "name": document["document_name"],
           "part": document["part"], "characters": len(document["text"]),
           "contentHash": digest(document), "capturedAt": record["capturedAt"]}
    return {**manifest, "documents": {**manifest["documents"], key: ref}}
