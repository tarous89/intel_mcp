"""Synthetic 1,000-trial export benchmark; no clinical data or model requests."""
import gzip
import json
import resource
import subprocess
import sys
import tempfile
from pathlib import Path

RUN = "12345678-1234-1234-1234-123456789abc"
with tempfile.TemporaryDirectory(prefix="dataset-benchmark-") as directory:
    source, target = Path(directory) / "input.jsonl.gz", Path(directory) / "output.xlsx"
    definitions = {f"variable_{i}": {"label": f"Variable {i}", "kind": "numeric", "source": "profile", "description": "Synthetic variable"} for i in range(40)}
    with gzip.open(source, "wt", encoding="utf8") as out:
        out.write(json.dumps({"version": 1, "tier": "max", "reportRunId": RUN, "trialCount": 1000, "definitions": definitions}) + "\n")
        for i in range(1000):
            trial_id = f"2024-{i:06d}-12-00"
            sites = [{"name": f"Institution {j}", "country": "DE", "investigators": [{"name": f"Investigator {k}", "email": f"pi{k}@example.org"} for k in range(3)]} for j in range(12)]
            profile = {"eu_number": trial_id, "profile_schema_version": "11.0.0", "profile": {"filtering_variables": {"title": f"Synthetic trial {i}", "eligibility": "Synthetic eligibility criterion. " * (4900 if i == 0 else 660)}, "classification_variables": {"sites": sites}}}
            row = {"trial_id": trial_id, "segment_keys": ["primary"], "values": {name: i + j for j, name in enumerate(definitions)}}
            out.write(json.dumps({"row": row, "profile": profile}) + "\n")
    import time
    started = time.monotonic()
    result = subprocess.run([sys.executable, "-m", "intel_mcp.report_dataset", str(source), str(target), RUN], capture_output=True, text=True, check=True)
    print(json.dumps({"workbook": json.loads(result.stdout), "elapsedSeconds": round(time.monotonic() - started, 2), "childPeakRssMiB": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1), "snapshotBytes": source.stat().st_size}))
