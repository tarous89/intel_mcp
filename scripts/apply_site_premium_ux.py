from pathlib import Path


def replace(path: str, old: str, new: str, count: int = 1):
    p = Path(path)
    text = p.read_text()
    actual = text.count(old)
    assert actual == count, (path, actual, old)
    p.write_text(text.replace(old, new))


replace(
    "src/intel_mcp/site_search.py",
    '    size = value.get("size", 25)\n',
    '    size = value.get("size", 10)\n',
)
replace(
    "src/intel_mcp/site_search.py",
    'or size not in {25, 50}:\n        raise SiteSearchError("Choose a valid result page and 25 or 50 rows.", 400)',
    'or size not in {10, 25, 50}:\n        raise SiteSearchError("Choose a valid result page and 10, 25 or 50 rows.", 400)',
)

context = Path("SITE_AGENT_CONTEXT.md")
text = context.read_text()
text = text.replace(
    "No pinning, enrichment, new variables,\npatient-count or capacity claims are supported. Unsupported edits fail without a replacement list.\n",
    "No pinning, enrichment, new variables, patient-count or capacity claims are supported. When a request\ncontains unsupported ideas, the revision function applies the closest useful supported part instead of\nreturning a semantic error. If the model produces an effective no-op, the server applies one conservative\nexisting-control change, so every accepted revision changes the list behavior. Missing original anchors are\nrepaired by retaining one immutable initial anchor. Provider/transport failures still fail closed.\n",
)
text = text.replace(
    "`/search` accepts service-authenticated `full_list: true` to return every matching Site/PI; omission\npreserves the top-10 preview. App must verify project ownership/payment before requesting or disclosing\nthese results.",
    "`/search` accepts bounded Premium pages of 10, 25 or 50 rows; 10 is the default page size. It also keeps\nservice-authenticated `full_list: true` only as a compatibility path. Omission preserves the top-10 preview.\nApp must verify project ownership/payment before requesting or disclosing these results.",
)
context.write_text(text)
print("Applied 10-row Premium paging and best-effort revision context.")
