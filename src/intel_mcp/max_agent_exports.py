"""Model-free, lossless dataset export and optional isolated PDF rendering."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from intel_mcp.report_dataset import fields, text_parts


def workbook(payload, target):
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    from openpyxl.styles import Font
    book = Workbook(write_only=True)
    book.properties.creator = "TrialAgents"
    book.properties.created = book.properties.modified = datetime(2000, 1, 1)
    sections = {
        "Manifest": payload["manifest"], "Profiles": payload["profiles"],
        "Documents": payload["documents"], "Facts": payload["work"].get("facts", []),
        "Definitions": payload["work"].get("definitions", {}),
        "Membership": payload["work"].get("membership", {}),
        "Membership sources": payload["work"].get("membershipSources", {}),
        "Rankings and results": payload["metrics"],
        "Assessments": payload["work"].get("assessments", []),
        "Validation": payload["issues"], "Scripts": payload.get("scripts", {}),
    }
    for name, value in sections.items():
        sheet = book.create_sheet(name)
        sheet.freeze_panes = "A2"
        sheet.append(["JSON pointer", "Type", "Part", "Value"])
        for pointer, kind, item in fields(value):
            # JSON escaping preserves XML-illegal characters losslessly.
            encoded = json.dumps(item, ensure_ascii=False, allow_nan=False)
            if ILLEGAL_CHARACTERS_RE.search(encoded):
                encoded = json.dumps(item, ensure_ascii=True, allow_nan=False)
            for part, chunk in enumerate(text_parts(encoded), 1):
                cells = []
                for val in (pointer, kind, part, chunk):
                    cell = WriteOnlyCell(sheet, value=val)
                    if isinstance(val, str):
                        cell.data_type = "s"  # Untrusted values can never become Excel formulas.
                    cells.append(cell)
                sheet.append(cells)
    book.save(target)
    # ZIP metadata is normalized so identical version inputs yield identical bytes.
    import zipfile
    original = Path(target).read_bytes()
    import io
    with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as dest:
        for name in sorted(source.namelist()):
            info = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            dest.writestr(info, source.read(name))


async def subprocess_export(payload_path, target):
    proc = await asyncio.create_subprocess_exec(sys.executable, "-m", "intel_mcp.max_agent_exports",
        str(payload_path), str(target), stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        await asyncio.wait_for(proc.wait(), 180)
        if proc.returncode:
            raise RuntimeError("Dataset export failed")
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()


async def optional_pdf(html_path, target):
    # Chromium's own sandbox remains enabled. Missing browser never kills HTML.
    binary = os.getenv("MAX_AGENT_CHROMIUM") or shutil.which("chromium") or shutil.which("google-chrome")
    if not binary:
        return False
    proc = await asyncio.create_subprocess_exec(binary, "--headless", "--disable-gpu",
        "--disable-background-networking", "--no-pdf-header-footer",
        "--user-data-dir=" + str(target.parent / "chromium"),
        "--print-to-pdf=" + str(target), html_path.as_uri(),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        await asyncio.wait_for(proc.wait(), 90)
        return proc.returncode == 0 and target.exists() and target.read_bytes()[:5] == b"%PDF-"
    except TimeoutError:
        return False
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()


if __name__ == "__main__":
    workbook(json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]))
