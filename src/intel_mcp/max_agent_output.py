"""Deterministic calculations and a static, sanitized report surface."""
from __future__ import annotations

import html
import json
import math
import statistics
from collections import defaultdict

TEMPLATE_VERSION = "max-broad-subgroups-1"
CSP = "sandbox; default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"
CSS = """
@page{size:A4;margin:17mm 15mm}*{box-sizing:border-box}body{font-family:Arial,sans-serif;color:#173b36;
font-size:15px;line-height:1.55;margin:0;background:#fff}main{max-width:1060px;margin:0 auto;padding:40px 28px}
h1{font-size:32px;line-height:1.2;letter-spacing:-.6px}h2{font-size:23px;margin-top:36px;border-top:1px solid #c8d8d1;padding-top:24px}
h3{font-size:18px}h1,h2,h3,h4{break-after:avoid}p,li{orphans:3;widows:3}section{margin:20px 0}
.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:1.3px}.executive,.evidence{background:#eef5ef;padding:18px 22px}
.chart-row{display:grid;grid-template-columns:minmax(140px,42%) 1fr 70px;gap:12px;align-items:center;margin:9px 0;break-inside:avoid}
.chart-label{overflow-wrap:anywhere}.bar{height:15px;background:#2d6456;min-width:0}.value{text-align:right;font-variant-numeric:tabular-nums}
figure{margin:22px 0}figcaption,.note{font-size:12px;color:#516760}.subgroup{border-left:3px solid #b5ce89;padding-left:16px;margin:20px 0}
table{width:100%;border-collapse:collapse;table-layout:fixed;margin:16px 0}th,td{text-align:left;vertical-align:top;padding:9px;
border-bottom:1px solid #dce5df;overflow-wrap:anywhere}thead{display:table-header-group}tr{break-inside:auto}
a{color:#2d6456;overflow-wrap:anywhere}.references{font-size:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere}
@media print{body{font-size:10.5pt;line-height:1.45}main{max-width:none;padding:0}h1{font-size:25pt}h2{font-size:18pt}
h3{font-size:13pt}.chart-row{grid-template-columns:42% 1fr 18mm;gap:3mm}figure,section,table{break-inside:auto}
.executive,.evidence{-webkit-print-color-adjust:exact;print-color-adjust:exact}.bar{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def pointer(value, path):
    if path == "":
        return value
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("A JSON Pointer is required")
    for token in path[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def validate_facts(work, profiles, documents):
    valid, errors = {}, []
    for fact in work.get("facts", []):
        if not isinstance(fact, dict):
            errors.append({"code": "unsupported_fact", "id": ""})
            continue
        try:
            fid, tid, source = fact["id"], fact["trialId"], fact["source"]
            if not isinstance(fid, str) or fid in valid or tid not in profiles:
                raise ValueError()
            if source.get("documentKey"):
                document = documents[source["documentKey"]]
                if document["trial_id"] != tid:
                    raise ValueError()
                text = document["text"]
            else:
                value = pointer(profiles[tid]["profile"], source["profilePath"])
                text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                if not source.get("quote") and fact["value"] != value:
                    raise ValueError()
            quote = source.get("quote")
            if quote is not None and (not isinstance(quote, str) or not quote.strip() or quote not in text):
                raise ValueError()
            if source.get("documentKey") and not quote:
                raise ValueError()
            valid[fid] = fact
        except (KeyError, ValueError, TypeError, IndexError, AttributeError):
            errors.append({"code": "unsupported_fact", "id": str(fact.get("id", ""))})
    return valid, errors


def calculate(metric, facts, members):
    """Compute complete label rankings with deduplicated contributing trial IDs."""
    method, group = metric["method"], metric["groupId"]
    membership = members.get(group, {})
    eligible = {tid for tid, state in membership.items() if state is True}
    denominator = set(metric.get("denominatorTrialIds", []))
    if denominator - eligible:
        raise ValueError("Denominator includes unknown or excluded members")
    buckets = defaultdict(dict)
    for observation in metric.get("observations", []):
        fact = facts[observation["factId"]]
        tid = fact["trialId"]
        if tid not in eligible:
            raise ValueError("Observation has unknown or excluded membership")
        label = str(observation.get("label", metric.get("title", "")))
        value = fact["value"]
        if method in {"count", "percentage"}:
            if value is False or value is None:
                continue
            value = 1
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("A finite measured value is required")
        if tid in buckets[label] and buckets[label][tid] != value:
            raise ValueError("Conflicting observations for the same trial")
        buckets[label][tid] = value
    rows = []
    for label, by_trial in buckets.items():
        values = list(by_trial.values())
        n = len(values)
        if not n:
            continue
        if method == "count":
            value = n
        elif method == "percentage":
            if not denominator or set(by_trial) - denominator:
                raise ValueError("Invalid percentage denominator")
            value = 100 * n / len(denominator)
        elif method == "mean":
            value = statistics.mean(values)
        elif method == "median":
            value = statistics.median(values)
        elif method == "min":
            value = min(values)
        elif method == "max":
            value = max(values)
        else:
            raise ValueError("Unsupported calculation method")
        rows.append({"label": label, "value": value, "n": n, "trialIds": sorted(by_trial),
                     "denominator": len(denominator) if method == "percentage" else n})
    rows.sort(key=lambda row: (-row["value"], row["label"].casefold()))
    return {**metric, "rows": rows}


def review(work, profiles, documents, plan):
    facts, issues = validate_facts(work, profiles, documents)
    members = work.get("membership", {})
    group_ids = [f"group_{i + 1}" for i, _ in enumerate(plan["studyCohorts"])]
    analysis_ids = [f"analysis_{i + 1}" for i, _ in enumerate(plan["reportSections"])]
    for group, assignment in members.items():
        if group not in group_ids or not isinstance(assignment, dict):
            raise ValueError("Invalid group membership")
        if any(tid not in profiles or state is not None and type(state) is not bool for tid, state in assignment.items()):
            raise ValueError("Invalid trial membership")
        for tid, state in assignment.items():
            sources = work.get("membershipSources", {}).get(group, {}).get(tid, [])
            if state is not None and (not sources or any(fid not in facts or facts[fid]["trialId"] != tid for fid in sources)):
                issues.append({"code": "invalid_membership", "groupId": group, "trialId": tid})
                assignment[tid] = None
            if group != "group_1" and state is True and members.get("group_1", {}).get(tid) is not True:
                issues.append({"code": "invalid_membership", "groupId": group, "trialId": tid})
                assignment[tid] = None
    metrics = {}
    for metric in work.get("metrics", []):
        try:
            if metric["analysisId"] not in analysis_ids or metric["groupId"] not in group_ids or metric["id"] in metrics:
                raise ValueError()
            computed = calculate(metric, facts, members)
            if computed["rows"]:
                metrics[metric["id"]] = computed
            else:
                issues.append({"code": "empty_metric", "id": metric["id"]})
        except (ValueError, TypeError, KeyError, AttributeError):
            issues.append({"code": "unsupported_metric", "id": str(metric.get("id", "")) if isinstance(metric, dict) else ""})
    covered = {(a.get("analysisId"), a.get("groupId")) for a in work.get("assessments", [])
               if a.get("disposition") in {"contributes", "not_applicable", "insufficient_evidence"} and a.get("reason")}
    for analysis in analysis_ids:
        for group in group_ids:
            if (analysis, group) not in covered:
                issues.append({"code": "missing_group_assessment", "analysisId": analysis, "groupId": group})
    return metrics, issues


def chart(metric):
    """Ten displayed rows; the complete ranking remains in calculation output."""
    rows = metric["rows"][:10]
    largest = max([abs(row["value"]) for row in rows] + [1])
    parts = ["<figure><h3>" + html.escape(str(metric.get("title", ""))) + "</h3>"]
    for row in rows:
        width = round(100 * abs(row["value"]) / largest, 3)
        value = f'{row["value"]:,.2f}'.rstrip("0").rstrip(".")
        # Signed results use a labelled value table; a magnitude-only bar would mislead.
        bar = f'<div class="bar" style="width:{width}%"></div>' if all(r["value"] >= 0 for r in rows) else ""
        parts.append('<div class="chart-row"><span class="chart-label">' + html.escape(row["label"]) +
                     '</span><div>' + bar + '</div><span class="value">' +
                     html.escape(value) + "</span></div>")
    if len(metric["rows"]) > 10:
        parts.append('<figcaption>Top 10 shown. The dataset contains the complete ranking.</figcaption>')
    if metric["method"] == "percentage":
        parts.append("<figcaption>Denominator: " + str(rows[0]["denominator"]) + " contributing trials; categories may overlap.</figcaption>")
    parts.append("</figure>")
    return "".join(parts)


ALLOWED = set("main section article header footer div span p h1 h2 h3 h4 h5 h6 ul ol li strong em b i small blockquote figure figcaption table thead tbody tfoot tr th td caption a br hr pre code dl dt dd sup sub".split())
DROP = set("script style iframe object embed link meta base form input button textarea select option svg math template noscript".split())


def render_html(raw, metrics, title):
    from lxml import etree
    from lxml import html as dom
    root = dom.fragment_fromstring(raw, create_parent="main")
    for element in list(root.iterdescendants()):
        if not isinstance(element.tag, str):
            element.getparent().remove(element)
            continue
        tag = element.tag.lower()
        if tag in DROP:
            element.drop_tree()
        elif tag not in ALLOWED:
            element.drop_tag()
        else:
            for name in list(element.attrib):
                if name not in {"class", "id", "href", "colspan", "rowspan", "data-chart", "data-role", "data-analysis"}:
                    del element.attrib[name]
            if "href" in element.attrib:
                href = element.attrib["href"].strip()
                if not (href.startswith("#") or href.startswith("https://")):
                    del element.attrib["href"]
                else:
                    element.attrib["rel"] = "noopener noreferrer"
            for name in ("colspan", "rowspan"):
                if name in element.attrib and not re_positive_integer(element.attrib[name]):
                    del element.attrib[name]
    for element in list(root.xpath("//*[@data-chart]")):
        metric = metrics.get(element.get("data-chart"))
        if not metric or element.get("data-role") == "main" and metric["groupId"] != "group_1":
            element.drop_tree()
            continue
        replacement = dom.fragment_fromstring(chart(metric))
        element.getparent().replace(element, replacement)
    content = etree.tostring(root, method="html", encoding="unicode")
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + \
           '<meta http-equiv="Content-Security-Policy" content="' + html.escape(CSP, quote=True) + '">' + \
           "<title>" + html.escape(title) + "</title><style>" + CSS + "</style></head><body>" + content + "</body></html>"


def re_positive_integer(value):
    return value.isdigit() and 1 <= int(value) <= 100
