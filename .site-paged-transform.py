from pathlib import Path

p=Path('src/intel_mcp/site_search.py')
s=p.read_text()
anchor='''\n\nasync def create_project_search(settings, engine, body: dict, *, transport=None) -> dict:\n'''
assert s.count(anchor)==1
addition=r'''

SITE_PAGE_METRICS = {
    "therapeuticAreaTrials", "diseaseMatchedTrials", "phaseMatchedTrials",
    "modalityMatchedTrials", "paediatricMatchedTrials", "recentActivityTrials",
}


def page_deterministic_result(result: dict, value: object) -> dict:
    """Return one bounded page from a fully ranked deterministic result.

    This deliberately pages before HTTP serialization. The MCP worker may hold the
    cohort while ranking it, but the App never receives or JSON-parses thousands of
    Site/PI records in one response.
    """
    if not isinstance(value, dict) or set(value) - {"kind", "page", "size", "controls"}:
        raise SiteSearchError("Invalid result page.", 400)
    kind = value.get("kind", "sites")
    page = value.get("page", 1)
    size = value.get("size", 25)
    controls = value.get("controls", {})
    if kind not in {"sites", "pis"} or type(page) is not int or not 1 <= page <= 1_000_000 or size not in {25, 50}:
        raise SiteSearchError("Choose a valid result page and 25 or 50 rows.", 400)
    if not isinstance(controls, dict) or set(controls) - {"sort", "search", "minimum_metric", "minimum_trials"}:
        raise SiteSearchError("Unsupported list controls.", 400)
    sort = controls.get("sort", "rank")
    search = controls.get("search", "")
    minimum_metric = controls.get("minimum_metric", "diseaseMatchedTrials")
    minimum_trials = controls.get("minimum_trials")
    if sort != "rank" and sort not in SITE_PAGE_METRICS:
        raise SiteSearchError("Unsupported result sort.", 400)
    if minimum_metric not in SITE_PAGE_METRICS or not isinstance(search, str) or len(search) > 160:
        raise SiteSearchError("Unsupported list controls.", 400)
    if minimum_trials is not None and (type(minimum_trials) is not int or not 0 <= minimum_trials <= 1_000_000):
        raise SiteSearchError("Unsupported minimum trial count.", 400)

    source = result.get(kind)
    if not isinstance(source, list):
        raise SiteSearchError("The deterministic result is incomplete.")
    needle = normalized_search = " ".join(search.casefold().split())

    def haystack(row: dict) -> str:
        values = [row.get("name"), row.get("country"), row.get("department"), row.get("email")]
        contact = row.get("contact")
        if isinstance(contact, dict):
            values.extend([contact.get("name"), contact.get("email")])
        for person in row.get("matchedPIs") or []:
            if isinstance(person, dict):
                values.extend([person.get("name"), person.get("department"), person.get("email")])
        for site in row.get("sites") or []:
            if isinstance(site, dict):
                values.extend([site.get("name"), site.get("country")])
        return " ".join(str(item or "").casefold() for item in values)

    rows = [row for row in source if isinstance(row, dict)]
    if needle:
        rows = [row for row in rows if needle in " ".join(haystack(row).split())]
    if minimum_trials is not None:
        rows = [
            row for row in rows
            if isinstance(row.get("metrics"), dict)
            and type(row["metrics"].get(minimum_metric)) is int
            and row["metrics"][minimum_metric] >= minimum_trials
        ]
    if sort == "rank":
        rows.sort(key=lambda row: (int(row.get("rank") or 0), str(row.get("id") or "")))
    else:
        rows.sort(key=lambda row: (
            row.get("metrics", {}).get(sort) is None,
            -(row.get("metrics", {}).get(sort) or 0),
            int(row.get("rank") or 0),
            str(row.get("id") or ""),
        ))
    total = len(rows)
    pages = max(1, (total + size - 1) // size)
    start = (page - 1) * size
    selected = rows[start:start + size] if page <= pages else []
    output = {**result, "sites": selected if kind == "sites" else [], "pis": selected if kind == "pis" else []}
    output["page"] = {"kind": kind, "page": page, "size": size, "pages": pages, "total": total}
    return output


async def search_page_deterministically(engine, criteria_value: object, page_value: object) -> dict:
    result = await search_deterministically(engine, criteria_value, full_list=True)
    return page_deterministic_result(result, page_value)
'''
s=s.replace(anchor,addition+anchor)
p.write_text(s)

p=Path('src/intel_mcp/site_search_routes.py')
s=p.read_text()
s=s.replace('''    search_deterministically,\n)''','''    search_deterministically,\n    search_page_deterministically,\n)''')
old='''            if "criteria" in body:\n                if set(body) - {"criteria", "full_list"} or type(body.get("full_list", False)) is not bool:\n                    raise SiteSearchError("Unsupported search parameters.", 400)\n                return await search_deterministically(engine_factory(), body["criteria"], full_list=body.get("full_list", False))'''
new='''            if "criteria" in body:\n                if set(body) - {"criteria", "full_list", "page"} or type(body.get("full_list", False)) is not bool:\n                    raise SiteSearchError("Unsupported search parameters.", 400)\n                if "page" in body:\n                    if body.get("full_list") is True:\n                        raise SiteSearchError("Choose a bounded page or a compatibility full list, not both.", 400)\n                    return await search_page_deterministically(engine_factory(), body["criteria"], body["page"])\n                return await search_deterministically(engine_factory(), body["criteria"], full_list=body.get("full_list", False))'''
assert s.count(old)==1
s=s.replace(old,new)
p.write_text(s)
