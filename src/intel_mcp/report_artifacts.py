from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import tempfile
from pathlib import Path

import httpx
from starlette.background import BackgroundTask
from starlette.responses import FileResponse, JSONResponse

from intel_mcp.light_report_execution import ReportExecutionControl
from intel_mcp.report_dataset import file_sha, write_snapshot

LOGGER = logging.getLogger("intel_mcp")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
EXPORT_SLOT = asyncio.Lock()
MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class ArtifactStore:
    def __init__(self, settings):
        self.settings = settings

    def url(self, run_id, sha, extension):
        if not UUID.fullmatch(run_id) or not SHA.fullmatch(sha) or extension not in {"jsonl.gz", "xlsx"}:
            raise ValueError("Invalid artifact identity")
        if not self.settings.engine_api_url or not self.settings.engine_service_token:
            raise ValueError("Report artifact storage is not configured")
        return f"{self.settings.engine_api_url}/api/internal/mcp/report-artifacts/{run_id}/{sha}.{extension}"

    async def upload(self, run_id, path, extension):
        sha = await asyncio.to_thread(file_sha, path)
        url = self.url(run_id, sha, extension)
        async def chunks():
            with path.open("rb") as source:
                while chunk := await asyncio.to_thread(source.read, 65536):
                    yield chunk
        async with httpx.AsyncClient(timeout=180) as client:
            for attempt in range(3):
                try:
                    response = await client.put(url, headers={"Authorization": f"Bearer {self.settings.engine_service_token}",
                        "Content-Length": str(path.stat().st_size), "Content-Type": "application/octet-stream"}, content=chunks())
                    response.raise_for_status()
                    if response.json().get("sha256") != sha:
                        raise ValueError("Stored artifact checksum mismatch")
                    return sha
                except httpx.HTTPError as error:
                    if isinstance(error, httpx.HTTPStatusError) and error.response.status_code < 500 and error.response.status_code != 429:
                        raise
                    if attempt == 2:
                        raise
                    await asyncio.sleep(attempt + 1)

    async def download(self, run_id, sha, extension, target):
        async with httpx.AsyncClient(timeout=180) as client:
            async with client.stream("GET", self.url(run_id, sha, extension), headers={"Authorization": f"Bearer {self.settings.engine_service_token}"}) as response:
                response.raise_for_status()
                size = 0
                with target.open("wb") as output:
                    async for chunk in response.aiter_bytes(65536):
                        size += len(chunk)
                        if size > 256 * 1024 * 1024:
                            raise ValueError("Oversized report artifact")
                        output.write(chunk)
        if await asyncio.to_thread(file_sha, target) != sha:
            raise ValueError("Downloaded artifact checksum mismatch")


async def save_dataset(settings, **kwargs):
    with tempfile.TemporaryDirectory(prefix="report-snapshot-") as directory:
        path = Path(directory) / "snapshot.jsonl.gz"
        manifest = await asyncio.to_thread(write_snapshot, path, **kwargs)
        await ArtifactStore(settings).upload(kwargs["report_run_id"], path, "jsonl.gz")
        return manifest


async def export_workbook(snapshot, target, run_id):
    # Isolate Excel allocations and temporary XML files; memory returns to the OS
    # when the child exits, and cancellation terminates the actual work.
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "intel_mcp.report_dataset", str(snapshot), str(target), run_id,
        env={**os.environ, "TMPDIR": str(target.parent)},
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        await asyncio.wait_for(process.wait(), timeout=180)
        if process.returncode:
            raise ValueError("Dataset workbook generation failed")
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


def register_report_dataset(mcp, settings, authorized):
    @mcp.custom_route("/internal/max-report/dataset/{report_run_id}", methods=["GET"])
    async def download(request):
        if not authorized(request):
            return JSONResponse({"error": "Unauthorized."}, status_code=401)
        run_id = request.path_params["report_run_id"]
        if not UUID.fullmatch(run_id):
            return JSONResponse({"error": "Invalid report ID."}, status_code=400)
        control = ReportExecutionControl(settings)
        directory = None
        try:
            # Only one workbook build per process; queue length is bounded by timeout.
            await asyncio.wait_for(EXPORT_SLOT.acquire(), timeout=2)
        except TimeoutError:
            return JSONResponse({"error": "Another dataset is being prepared. Please try again shortly."}, status_code=503, headers={"Retry-After": "5"})
        try:
            run = await control.load(run_id)
            if run.get("tier") != "max" or run.get("status") != "completed":
                return JSONResponse({"error": "A completed Max report is required."}, status_code=403)
            manifest = (run.get("finalReport") or {}).get("dataset") or {}
            snapshot_sha = manifest.get("snapshotSha", "")
            if manifest.get("version") != 1 or not isinstance(snapshot_sha, str) or not SHA.fullmatch(snapshot_sha):
                return JSONResponse({"error": "This report has no saved dataset. Dataset downloads are available for new Max reports."}, status_code=404)
            directory = tempfile.TemporaryDirectory(prefix="report-export-")
            path = Path(directory.name) / "dataset.xlsx"
            store = ArtifactStore(settings)
            cached = manifest.get("xlsxSha", "")
            if not isinstance(cached, str) or not SHA.fullmatch(cached):
                cached = ""
            if isinstance(cached, str) and SHA.fullmatch(cached):
                try:
                    await store.download(run_id, cached, "xlsx", path)
                except httpx.HTTPStatusError as error:
                    if error.response.status_code != 404:
                        raise
                    cached = ""
            if not cached:
                snapshot = Path(directory.name) / "snapshot.jsonl.gz"
                await store.download(run_id, snapshot_sha, "jsonl.gz", snapshot)
                await export_workbook(snapshot, path, run_id)
                xlsx_sha = await store.upload(run_id, path, "xlsx")
                await control._post({"action": "dataset", "reportRunId": run_id, "snapshotSha": snapshot_sha, "xlsxSha": xlsx_sha})
            response = FileResponse(path, media_type=MIME, filename=f"max-report-dataset-{run_id}.xlsx",
                headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}, background=BackgroundTask(directory.cleanup))
            directory = None
            return response
        except Exception as error:
            LOGGER.warning("Report dataset download failed: run=%s error_type=%s", run_id, type(error).__name__)
            return JSONResponse({"error": "The dataset could not be prepared. Please try again."}, status_code=503)
        finally:
            if directory is not None:
                directory.cleanup()
            EXPORT_SLOT.release()
