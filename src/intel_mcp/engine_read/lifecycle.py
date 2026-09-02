from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from typing import Any


_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_COUNTRY_CODES = {
    "austria": "AT", "belgium": "BE", "bulgaria": "BG", "croatia": "HR",
    "cyprus": "CY", "czechia": "CZ", "czech republic": "CZ", "denmark": "DK",
    "estonia": "EE", "finland": "FI", "france": "FR", "germany": "DE",
    "greece": "GR", "hungary": "HU", "iceland": "IS", "ireland": "IE",
    "italy": "IT", "latvia": "LV", "liechtenstein": "LI", "lithuania": "LT",
    "luxembourg": "LU", "malta": "MT", "netherlands": "NL", "norway": "NO",
    "poland": "PL", "portugal": "PT", "romania": "RO", "slovakia": "SK",
    "slovenia": "SI", "spain": "ES", "sweden": "SE",
}
_POSITIVE_AUTHORIZATION_OUTCOMES = {
    "authorised", "authorisedwithconditions", "authorized",
    "authorizedwithconditions", "approved", "approvedwithconditions",
}
_UPDATE_ORDER = {
    "part_i_submission": 10, "part_ii_submission": 20,
    "part_i_assessment": 30, "part_ii_assessment": 40,
    "initial_decision": 50, "authorization_decision": 50,
    "application_decision": 50, "country_status": 60,
    "trial_status": 70, "trial_start": 80, "trial_restart": 80,
    "recruitment_status": 90, "trial_end": 100,
}


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _text(value: Any) -> str | None:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        result = str(value).strip()
        return result or None
    if isinstance(value, dict):
        for key in ("name", "value", "label", "description", "displayName"):
            result = _text(value.get(key))
            if result:
                return result
    return None


def _iso_date(value: Any) -> str | None:
    raw = _text(value)
    if not raw:
        return None
    match = _DATE_RE.search(raw)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1)).isoformat()
    except ValueError:
        return None


def _valid_dependent_date(
    submission_date: str | None, dependent_date: str | None
) -> str | None:
    if not dependent_date:
        return None
    if submission_date and dependent_date < submission_date:
        return None
    return dependent_date


def _country_code(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in (
        "mscCountryCode", "countryCode", "memberStateCode",
        "concernedMemberStateCode", "mscCode", "country", "countryName",
        "mscName",
    ):
        raw = _text(value.get(key))
        if not raw:
            continue
        if len(raw) == 2 and raw.isalpha():
            return raw.upper()
        mapped = _COUNTRY_CODES.get(raw.casefold())
        if mapped:
            return mapped
    for nested_key in ("mscInfo", "memberStateInfo", "mscList"):
        nested = value.get(nested_key)
        values = nested if isinstance(nested, list) else [nested]
        for item in values:
            result = _country_code(item)
            if result:
                return result
    return None


def _normalise_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", (_text(value) or "").casefold())


def _normalise_outcome(value: Any) -> str | None:
    raw = _text(value)
    if not raw:
        return None
    key = _normalise_key(raw)
    if any(term in key for term in ("notauthor", "unauthor", "denied")):
        return "Not authorised"
    if "reject" in key or "refus" in key or "notaccept" in key:
        return "Rejected"
    if "condition" in key and ("author" in key or "approv" in key):
        return "Authorised with conditions"
    if "author" in key or "approv" in key:
        return "Authorised"
    if "accept" in key:
        return "Acceptable"
    if "withdraw" in key:
        return "Withdrawn"
    if "lapse" in key:
        return "Lapsed"
    return raw[:1].upper() + raw[1:]


def _normalise_status(value: Any) -> str | None:
    raw = _text(value)
    if not raw:
        return None
    mapping = {
        "underevaluation": "Under evaluation", "authorised": "Authorised",
        "authorized": "Authorised", "halted": "Temporarily halted",
        "temporarilyhalted": "Temporarily halted", "ended": "Ended",
        "earlyterminated": "Early terminated", "recruiting": "Recruiting",
        "recruitmentended": "Ended", "trialstarted": "Started",
    }
    return mapping.get(_normalise_key(raw), raw[:1].upper() + raw[1:])


def _is_positive_authorization(value: Any) -> bool:
    return _normalise_key(value) in _POSITIVE_AUTHORIZATION_OUTCOMES


def _is_initial_application(application: dict[str, Any]) -> bool:
    business_key = (_text(application.get("businessKey")) or "").upper()
    application_type = (_text(application.get("type")) or "").upper()
    return business_key in {"IN", "INITIAL"} or "INITIAL" in application_type


def _is_additional_member_state_application(application: dict[str, Any]) -> bool:
    business_key = (_text(application.get("businessKey")) or "").upper()
    application_type = (_text(application.get("type")) or "").upper()
    return (
        business_key.startswith(("AMSC", "ADDMSC"))
        or "ADDITIONAL MEMBER STATE" in application_type
        or "ADDITIONAL MSC" in application_type
    )


def _is_transitioned_trial(ctis_json: dict[str, Any]) -> bool:
    authorized = ctis_json.get("authorizedApplication")
    eudract = authorized.get("eudraCt") if isinstance(authorized, dict) else None
    if not isinstance(eudract, dict):
        return False
    value = eudract.get("isTransitioned")
    return value is True or _normalise_key(value) in {"1", "true", "yes"}


def _application_label(application: dict[str, Any]) -> str:
    business_key = _text(application.get("businessKey")) or ""
    application_type = _text(application.get("type")) or ""
    key = business_key.upper()
    if _is_initial_application(application):
        return "Initial application"
    match = re.fullmatch(r"SM-(\d+)", key)
    if match:
        return f"Substantial modification {match.group(1)}"
    match = re.fullmatch(r"NSM-(\d+)", key)
    if match:
        return f"Non-substantial modification {match.group(1)}"
    if _is_additional_member_state_application(application):
        return "Additional Member State application"
    return business_key or application_type or "Application"


def _applications(ctis_json: dict[str, Any]) -> list[dict[str, Any]]:
    authorized = ctis_json.get("authorizedApplication")
    values = authorized.get("applicationInfo") if isinstance(authorized, dict) else None
    if not isinstance(values, list):
        return []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for application in values:
        if not isinstance(application, dict):
            continue
        identity = _text(application.get("businessKey")) or str(application.get("id") or "")
        if identity and identity in seen:
            continue
        if identity:
            seen.add(identity)
        result.append(application)
    return result


def _application_country_codes(application: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for field in ("ctMSCsByApplication", "decisions", "partIIInfo"):
        values = application.get(field)
        if not isinstance(values, list):
            continue
        for item in values:
            code = _country_code(item)
            if code:
                result.add(code)
    return result


def _part_ii_nodes(application: dict[str, Any], country_code: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for field in ("partIIInfo", "partII", "partIIs"):
        value = application.get(field)
        values = value if isinstance(value, list) else [value]
        for node in values:
            if isinstance(node, dict) and _country_code(node) == country_code:
                result.append(node)
    return result


def _authorized_part_ii_nodes(ctis_json: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    authorized = ctis_json.get("authorizedApplication")
    part_ii = authorized.get("authorizedPartII") if isinstance(authorized, dict) else None
    result: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(part_ii, dict):
        return result
    for field in ("authorizedPartsII", "memberStateApplications"):
        values = part_ii.get(field)
        if not isinstance(values, list):
            continue
        for node in values:
            code = _country_code(node)
            if isinstance(node, dict) and code:
                result.setdefault(code, []).append(node)
    return result


def _explicit_part_ii_submission_date(node: dict[str, Any]) -> str | None:
    """Exclude mscInfo.fromDate: its Part II submission semantics are unverified."""
    for field in (
        "initialPartIISubmissionDate", "partIISubmissionDate",
        "initialSubmissionDate", "submissionDate",
    ):
        parsed = _iso_date(node.get(field))
        if parsed:
            return parsed
    return None


def _part_ii_conclusion_date(node: dict[str, Any]) -> str | None:
    for field in (
        "partIIConclusionDate", "conclusionDate", "assessmentOutcomeDate",
        "assessmentCompletionDate",
    ):
        parsed = _iso_date(node.get(field))
        if parsed:
            return parsed
    return None


def _part_ii_conclusion_outcome(node: dict[str, Any]) -> str | None:
    for field in ("partIIConclusion", "conclusion", "assessmentOutcome", "outcome"):
        result = _normalise_outcome(node.get(field))
        if result:
            return result
    return None


def _update(
    *, date_value: str | None, label: str, outcome: str | None, kind: str,
    country_code: str | None = None,
) -> dict[str, Any] | None:
    if not date_value:
        return None
    return {
        "date": date_value, "label": label, "outcome": outcome,
        "_kind": kind, "_order": _UPDATE_ORDER[kind],
        "_country_code": country_code,
    }


def _public_country_update(update: dict[str, Any]) -> dict[str, Any]:
    return {"date": update["date"], "label": update["label"], "outcome": update["outcome"]}


def _public_overall_update(update: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": update["date"], "label": update["label"],
        "outcome": update["outcome"], "country_code": update["_country_code"],
    }


def _ordered_updates(updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(updates, key=lambda item: (
        item["date"], item["_order"], item["label"], item["outcome"] or "",
    ))


def _deduplicate_updates(updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered_updates = _ordered_updates(updates)
    formal_authorization_dates = {
        item["date"]
        for item in ordered_updates
        if item["_kind"] in {"initial_decision", "authorization_decision", "application_decision"}
        and _is_positive_authorization(item["outcome"])
    }
    result: list[dict[str, Any]] = []
    exact_seen: set[tuple[str, str, str | None]] = set()
    last_status: dict[str, str | None] = {}
    for item in ordered_updates:
        identity = (item["date"], item["label"], item["outcome"])
        if identity in exact_seen:
            continue
        exact_seen.add(identity)
        if (
            item["_kind"] == "country_status"
            and _is_positive_authorization(item["outcome"])
            and item["date"] in formal_authorization_dates
        ):
            continue
        if item["_kind"] in {"country_status", "trial_status", "recruitment_status"}:
            if item["label"] in last_status and last_status[item["label"]] == item["outcome"]:
                continue
            last_status[item["label"]] = item["outcome"]
        result.append(item)
    return result


def _country_state_nodes(ctis_json: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for node in _walk(ctis_json):
        if not any(key in node for key in (
            "clinicalTrialStatusHistory", "trialPeriod", "trialRecruitmentPeriod",
            "activeTrialPeriod", "activeTrialRecruitmentPeriod",
        )):
            continue
        code = _country_code(node)
        if code:
            result[code] = node
    return result


def _country_event_groups(ctis_json: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for node in _walk(ctis_json):
        events = node.get("events")
        if not isinstance(events, list) or not any(
            isinstance(event, dict) and event.get("notificationType") for event in events
        ):
            continue
        code = _country_code(node)
        if code:
            result[code] = node
    return result


def _country_status_updates(
    state: dict[str, Any], *, transitioned: bool
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    values = state.get("clinicalTrialStatusHistory")
    if not isinstance(values, list):
        return result
    for item in values:
        if not isinstance(item, dict):
            continue
        update = _update(
            date_value=_iso_date(item.get("trialStatusDate") or item.get("date")),
            label="CTIS transition status" if transitioned else "Country regulatory status",
            outcome=_normalise_status(item.get("trialStatus") or item.get("status")),
            kind="country_status",
        )
        if update and update["outcome"]:
            result.append(update)
    return result


_NOTIFICATION_UPDATES = {
    "START_OF_TRIAL": ("Trial started", None, "trial_start"),
    "RESTART_OF_TRIAL": ("Trial restarted", None, "trial_restart"),
    "START_OF_RECRUITMENT": ("Recruitment status", "Recruiting", "recruitment_status"),
    "RESTART_OF_RECRUITMENT": ("Recruitment status", "Recruiting", "recruitment_status"),
    "END_OF_RECRUITMENT": ("Recruitment status", "Ended", "recruitment_status"),
    "TEMPORARY_HALT": ("Trial status", "Temporarily halted", "trial_status"),
    "END_OF_TRIAL": ("Trial ended", None, "trial_end"),
    "EARLY_TERMINATION": ("Trial ended early", None, "trial_end"),
}


def _notification_updates(group: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    termination_reason = _text(group.get("earlyTerminationReason"))
    for event in group.get("events") or []:
        if not isinstance(event, dict):
            continue
        definition = _NOTIFICATION_UPDATES.get(str(event.get("notificationType") or "").upper())
        if not definition:
            continue
        label, outcome, kind = definition
        if label == "Trial ended early" and termination_reason:
            outcome = termination_reason
        update = _update(
            date_value=_iso_date(event.get("date")), label=label,
            outcome=outcome, kind=kind,
        )
        if update:
            result.append(update)
    return result


def _period_nodes(state: dict[str, Any], *fields: str) -> Iterable[dict[str, Any]]:
    for field in fields:
        value = state.get(field)
        values = value if isinstance(value, list) else [value]
        for item in values:
            if isinstance(item, dict):
                yield item


def _period_updates(state: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for period in _period_nodes(state, "activeTrialPeriod", "trialPeriod"):
        for field, label, kind in (
            ("trialStartDate", "Trial started", "trial_start"),
            ("trialEndDate", "Trial ended", "trial_end"),
        ):
            update = _update(
                date_value=_iso_date(period.get(field)), label=label,
                outcome=None, kind=kind,
            )
            if update:
                result.append(update)
    for period in _period_nodes(state, "activeTrialRecruitmentPeriod", "trialRecruitmentPeriod"):
        for field, outcome in (
            ("recruitmentStartDate", "Recruiting"),
            ("recruitmentEndDate", "Ended"),
        ):
            update = _update(
                date_value=_iso_date(period.get(field)), label="Recruitment status",
                outcome=outcome, kind="recruitment_status",
            )
            if update:
                result.append(update)
    return result


def _temporary_halt_updates(ctis_json: dict[str, Any], country_code: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in _walk(ctis_json):
        values = node.get("temporaryHaltList")
        if not isinstance(values, list):
            continue
        for halt in values:
            if not isinstance(halt, dict) or _country_code(halt) != country_code:
                continue
            for field, outcome in (("haltDate", "Temporarily halted"), ("restartDate", "Restarted")):
                update = _update(
                    date_value=_iso_date(halt.get(field)), label="Trial status",
                    outcome=outcome, kind="trial_status",
                )
                if update:
                    result.append(update)
    return result


def _application_updates(
    application: dict[str, Any], country_code: str, *, transitioned: bool
) -> list[dict[str, Any]]:
    label = _application_label(application)
    application_submission = _iso_date(application.get("submissionDate"))
    updates: list[dict[str, Any]] = []
    initial_prefix = "CTIS transition" if transitioned else "Initial"
    for node in _part_ii_nodes(application, country_code):
        part_ii_submission = _explicit_part_ii_submission_date(node)
        submission_update = _update(
            date_value=part_ii_submission,
            label=f"{initial_prefix} Part II application" if _is_initial_application(application)
            else f"{label} Part II application",
            outcome="Submitted", kind="part_ii_submission",
        )
        if submission_update:
            updates.append(submission_update)
        conclusion_update = _update(
            date_value=_valid_dependent_date(part_ii_submission, _part_ii_conclusion_date(node)),
            label=f"{initial_prefix} Part II assessment" if _is_initial_application(application)
            else f"{label} Part II assessment",
            outcome=_part_ii_conclusion_outcome(node), kind="part_ii_assessment",
        )
        if conclusion_update:
            updates.append(conclusion_update)

    decision_kind = "initial_decision" if _is_initial_application(application) else (
        "authorization_decision" if _is_additional_member_state_application(application)
        else "application_decision"
    )
    decision_label = (
        "CTIS transition decision"
        if transitioned and _is_initial_application(application)
        else "Initial country decision"
        if _is_initial_application(application)
        else f"{label} decision"
    )
    decisions = application.get("decisions")
    if isinstance(decisions, list):
        for decision in decisions:
            if not isinstance(decision, dict) or _country_code(decision) != country_code:
                continue
            update = _update(
                date_value=_valid_dependent_date(
                    application_submission, _iso_date(decision.get("decisionDate"))
                ),
                label=decision_label,
                outcome=_normalise_outcome(
                    decision.get("decision") or decision.get("decisionOutcome")
                ),
                kind=decision_kind,
            )
            if update:
                updates.append(update)
    return updates


def _country_lifecycle(
    *, country_code: str, applications: list[dict[str, Any]],
    state: dict[str, Any], event_group: dict[str, Any],
    authorized_part_ii_nodes: list[dict[str, Any]], ctis_json: dict[str, Any],
    transitioned: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updates: list[dict[str, Any]] = []
    for application in applications:
        if country_code in _application_country_codes(application):
            updates.extend(
                _application_updates(
                    application, country_code, transitioned=transitioned
                )
            )
    for node in authorized_part_ii_nodes:
        msc_info = node.get("mscInfo")
        source = msc_info if isinstance(msc_info, dict) else node
        submission = (
            _explicit_part_ii_submission_date(node)
            or _explicit_part_ii_submission_date(source)
        )
        update = _update(
            date_value=submission,
            label=(
                "CTIS transition Part II application"
                if transitioned else "Initial Part II application"
            ),
            outcome="Submitted", kind="part_ii_submission",
        )
        if update:
            updates.append(update)
        conclusion = _update(
            date_value=_valid_dependent_date(
                submission,
                _part_ii_conclusion_date(node) or _part_ii_conclusion_date(source),
            ),
            label=(
                "CTIS transition Part II assessment"
                if transitioned else "Initial Part II assessment"
            ),
            outcome=(
                _part_ii_conclusion_outcome(node)
                or _part_ii_conclusion_outcome(source)
            ),
            kind="part_ii_assessment",
        )
        if conclusion:
            updates.append(conclusion)
        decision = _update(
            date_value=_valid_dependent_date(
                submission, _iso_date(source.get("decisionDate"))
            ),
            label=(
                "CTIS transition decision"
                if transitioned else "Initial country decision"
            ),
            outcome=_normalise_outcome(
                source.get("decision") or source.get("decisionOutcome")
            ),
            kind="initial_decision",
        )
        if decision:
            updates.append(decision)
    updates.extend(_country_status_updates(state, transitioned=transitioned))
    updates.extend(_notification_updates(event_group))
    updates.extend(_period_updates(state))
    updates.extend(_temporary_halt_updates(ctis_json, country_code))
    for update in updates:
        update["_country_code"] = country_code

    updates = _deduplicate_updates(updates)
    return ({
        "country_code": country_code,
        "updates": [_public_country_update(item) for item in updates],
    }, updates)


def _overall_updates(
    applications: list[dict[str, Any]], country_updates: list[dict[str, Any]],
    *, transitioned: bool,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    initial = next((item for item in applications if _is_initial_application(item)), None)
    if initial:
        submission = _iso_date(initial.get("submissionDate"))
        part_i_submission = _update(
            date_value=submission,
            label=(
                "CTIS transition Part I application"
                if transitioned else "Initial Part I application"
            ),
            outcome="Submitted", kind="part_i_submission",
        )
        if part_i_submission:
            result.append(part_i_submission)
        part_i = initial.get("partI")
        part_i = part_i if isinstance(part_i, dict) else {}
        part_i_assessment = _update(
            date_value=_valid_dependent_date(
                submission, _iso_date(part_i.get("assessmentOutcomeDate"))
            ),
            label=(
                "CTIS transition Part I assessment"
                if transitioned else "Initial Part I assessment"
            ),
            outcome=_normalise_outcome(part_i.get("assessmentOutcome")),
            kind="part_i_assessment",
        )
        if part_i_assessment:
            result.append(part_i_assessment)
    first_part_ii = min(
        (item for item in country_updates if item["_kind"] == "part_ii_submission"),
        key=lambda item: (item["date"], item["_country_code"] or ""), default=None,
    )
    if first_part_ii:
        result.append({**first_part_ii, "label": "First Part II submission", "outcome": "Submitted"})
    first_decision = min(
        (item for item in country_updates if item["_kind"] == "initial_decision"),
        key=lambda item: (item["date"], item["_country_code"] or ""), default=None,
    )
    if first_decision:
        result.append({
            **first_decision,
            "label": (
                "First CTIS transition country decision"
                if transitioned else "First country decision"
            ),
        })
    first_authorization = min(
        (item for item in country_updates
         if item["_kind"] in {"initial_decision", "authorization_decision"}
         and _is_positive_authorization(item["outcome"])),
        key=lambda item: (item["date"], item["_country_code"] or ""), default=None,
    )
    if first_authorization and not (
        first_decision
        and first_authorization["date"] == first_decision["date"]
        and first_authorization["_country_code"] == first_decision["_country_code"]
        and first_authorization["outcome"] == first_decision["outcome"]
    ):
        result.append({**first_authorization, "label": "First country authorization"})
    result.sort(key=lambda item: (
        item["date"], item["_order"], item["label"], item["_country_code"] or "",
    ))
    return result


def build_ctis_lifecycle(ctis_json: dict[str, Any]) -> dict[str, Any]:
    """Build Trial Profile 9.0 deterministic overall and country timelines."""
    applications = _applications(ctis_json)
    transitioned = _is_transitioned_trial(ctis_json)
    state_nodes = _country_state_nodes(ctis_json)
    event_groups = _country_event_groups(ctis_json)
    part_ii_nodes = _authorized_part_ii_nodes(ctis_json)
    country_codes = set(state_nodes) | set(event_groups) | set(part_ii_nodes)
    for application in applications:
        country_codes.update(_application_country_codes(application))
    countries: list[dict[str, Any]] = []
    all_country_updates: list[dict[str, Any]] = []
    for code in sorted(country_codes):
        country, updates = _country_lifecycle(
            country_code=code, applications=applications,
            state=state_nodes.get(code, {}), event_group=event_groups.get(code, {}),
            authorized_part_ii_nodes=part_ii_nodes.get(code, []), ctis_json=ctis_json,
            transitioned=transitioned,
        )
        countries.append(country)
        all_country_updates.extend(updates)
    return {
        "overall_updates": [
            _public_overall_update(item)
            for item in _overall_updates(
                applications, all_country_updates, transitioned=transitioned
            )
        ],
        "countries": countries,
    }

