"""Private, immutable input for the shared project service.

This is NOT a tool result: full source profiles must never be returned to the
model/widget by this serializer. It does no I/O and never repeats a search.
"""
from copy import deepcopy
import hashlib
import json

from .selection import SelectionDataset, SelectionError

VERSION = "intel-prepared-selection-1"
MAX_PROFILE_BYTES = 16 * 1024 * 1024


def prepare_selection(dataset: SelectionDataset) -> dict:
    """Freeze the exact flexible selection, including overlapping memberships.

    Hash the transmitted JSON bytes, not a reserialized JSON object: Python and
    JavaScript serialize numbers differently. These hashes identify captured
    content; they are deliberately not advertised as Engine source revisions.
    """
    # A mutable source record or criteria object must not be published under the
    # old selection identity. This recomputes only a bounded content digest.
    current = SelectionDataset(dataset.criteria, list(dataset.records.values()))
    dataset.check_snapshot(current.snapshot)
    records = []
    byte_count = 0
    for trial_id, record in sorted(dataset.records.items()):
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False)
        raw = encoded.encode("utf-8")
        byte_count += len(raw)
        if byte_count > MAX_PROFILE_BYTES:
            raise SelectionError("COHORT_BYTES_EXCEEDED")
        records.append({"trial_id": trial_id, "json": encoded,
                        "sha256": hashlib.sha256(raw).hexdigest()})
    if not records:
        raise SelectionError("EMPTY_SELECTION")
    return {
        "version": VERSION,
        "selection_snapshot": dataset.snapshot,
        "criteria": deepcopy(dataset.criteria.model_dump(mode="json")),
        "selection_origin": deepcopy(getattr(dataset, "selection_origin", None)),
        "provenance": "captured-profile-content",
        "records": records,
    }
