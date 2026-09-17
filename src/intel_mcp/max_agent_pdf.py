"""Retry derivative PDFs from the exact published, sanitized HTML; no model calls."""
from pathlib import Path
import logging
import tempfile

import httpx

from intel_mcp.max_agent_exports import optional_pdf

LOGGER = logging.getLogger("intel_mcp.max_agent")


async def retry_pdf(control, artifacts):
    result = await control.call("claim_pdf")
    job = result.get("job")
    if not job:
        return False
    payload = {"reportRunId": job["report_run_id"], "version": job["version"], "claimToken": job["claim_token"]}
    try:
        with tempfile.TemporaryDirectory(prefix="max-pdf-retry-") as directory:
            source, target = Path(directory) / "report.html", Path(directory) / "report.pdf"
            await artifacts.download(job["report_run_id"], job["html_sha"], "html", source)
            if not await optional_pdf(source, target):
                raise RuntimeError("PDF renderer unavailable")
            sha = await artifacts.upload(job["report_run_id"], target, "pdf")
            await control.call("complete_pdf", **payload, pdfSha=sha)
    except Exception as error:
        if not isinstance(error, httpx.HTTPStatusError) or error.response.status_code != 409:
            LOGGER.warning("PDF retry pending report=%s version=%s", job["report_run_id"], job["version"])
            await control.call("retry_pdf", **payload)
    return True
