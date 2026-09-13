from types import SimpleNamespace

import pytest
from starlette.requests import Request

from intel_mcp import report_artifacts as artifacts

RUN = "12345678-1234-1234-1234-123456789abc"
SNAPSHOT, XLSX = "a" * 64, "b" * 64


@pytest.mark.anyio
@pytest.mark.parametrize("case, expected", [("unauthorized", 401), ("light", 403), ("running", 403), ("historic", 404), ("new", 200), ("cached", 200), ("bad_cache", 200)])
async def test_download_boundary_uses_frozen_snapshot_and_cache(monkeypatch, case, expected):
    calls = []
    class MCP:
        def custom_route(self, *_args, **_kwargs):
            def register(fn):
                self.handler = fn
                return fn
            return register
    class Control:
        def __init__(self, _): pass
        async def load(self, run_id):
            calls.append("load")
            assert run_id == RUN
            return {"tier": "light" if case == "light" else "max", "status": "running" if case == "running" else "completed",
                "finalReport": {"dataset": {} if case == "historic" else {"version": 1, "snapshotSha": SNAPSHOT,
                    "xlsxSha": XLSX if case == "cached" else ("invalid" if case == "bad_cache" else "")}}}
        async def _post(self, body):
            assert body == {"action": "dataset", "reportRunId": RUN, "snapshotSha": SNAPSHOT, "xlsxSha": XLSX}
            calls.append("cache")
    class Store:
        def __init__(self, _): pass
        async def download(self, run_id, sha, ext, path):
            calls.append(ext)
            assert run_id == RUN and sha == (SNAPSHOT if ext == "jsonl.gz" else XLSX)
            path.write_bytes(b"synthetic")
        async def upload(self, run_id, path, ext):
            assert run_id == RUN and ext == "xlsx" and path.read_bytes() == b"workbook"
            calls.append("upload")
            return XLSX
    async def export(snapshot, target, run_id):
        assert snapshot.read_bytes() == b"synthetic" and run_id == RUN
        calls.append("build")
        target.write_bytes(b"workbook")
    monkeypatch.setattr(artifacts, "ReportExecutionControl", Control)
    monkeypatch.setattr(artifacts, "ArtifactStore", Store)
    monkeypatch.setattr(artifacts, "export_workbook", export)
    mcp = MCP()
    artifacts.register_report_dataset(mcp, SimpleNamespace(), lambda _: case != "unauthorized")
    response = await mcp.handler(Request({"type": "http", "path_params": {"report_run_id": RUN}}))
    assert response.status_code == expected
    if case == "unauthorized": assert not calls
    if case == "cached": assert calls == ["load", "xlsx"]
    if case in {"new", "bad_cache"}: assert calls == ["load", "jsonl.gz", "build", "upload", "cache"]
    if expected == 200:
        assert response.media_type == artifacts.MIME
        await response.background()
