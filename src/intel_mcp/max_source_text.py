"""Bounded, model-free access to existing clinical profile text.

Full source stays in the shared profile store and downloadable dataset. These
verbatim excerpts supplement (never replace) the once-per-trial extraction.
"""
from __future__ import annotations

import re
from typing import Any

SOURCE_TEXT_BUDGET = 60_000  # total characters per objective, independent of pool size
SCREEN_ELIGIBILITY_BUDGET = 1_200  # per candidate, no additional model call
_PATHS = (
    ('classification_variables', 'trial_title'),
    ('classification_variables', 'primary_objectives'),
    ('classification_variables', 'secondary_objectives'),
    ('classification_variables', 'endpoints'),
    ('classification_variables', 'target_population_summary'),
    ('classification_variables', 'classification_summary'),
    ('filtering_variables', 'inclusion_criteria'),
    ('filtering_variables', 'exclusion_criteria'),
)
_STOP = set('the and for with from that this trial trials study studies analysis assess planned compare clinical report requested using'.split())


def _strings(value: Any):
    if isinstance(value, str) and value.strip():
        yield value.strip()
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def source_passages(profile: dict, query: str, maximum: int, *, eligibility_only: bool = False) -> str:
    """Select exact text windows across the source, not only its leading fields."""
    terms = set(re.findall(r'[a-z0-9]{3,}', query.casefold())) - _STOP
    candidates = []
    for path_index, (section, field) in enumerate(_PATHS):
        if eligibility_only and section != 'filtering_variables':
            continue
        value = (profile.get(section) or {}).get(field)
        for text in _strings(value):
            # Bound each excerpt, retaining overlapping context in long criteria.
            width = max(40, min(280, maximum // 2 - 40))
            for start in range(0, len(text), max(1, width - 80)):
                passage = text[start:start + width]
                score = len(terms & set(re.findall(r'[a-z0-9]{3,}', passage.casefold())))
                priority = 10_000 if field == 'trial_title' and start == 0 else score
                candidates.append((-priority, path_index, start, field, passage))
    chosen, used = [], 0
    for _, _, start, field, passage in sorted(candidates):
        entry = f'{field} (excerpt): {passage}'
        if used + len(entry) + 1 > maximum:
            continue
        if any(passage in previous for previous in chosen):
            continue
        chosen.append(entry)
        used += len(entry) + 1
    return '\n'.join(chosen)
