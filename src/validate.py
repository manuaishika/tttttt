"""Record validation. Pure functions: take dict-like records, return a list of Issues.

Errors block a record from the published dataset (it goes to excluded_records.csv with the
reason). Warnings keep the record but are reported in the run summary.

The checks encode the project's integrity rules, e.g. a record can only claim
'primary_source' if its publisher really is a government/academic source, and can only
claim 'corroborated' if more than one publisher is on record.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from . import schema as S
from .reference import REGION_BY_NAME

# Rough bounding box for India incl. islands; catches swapped/garbage coordinates.
INDIA_BBOX = (6.0, 37.5, 68.0, 98.0)  # lat_min, lat_max, lon_min, lon_max


@dataclass(frozen=True)
class Issue:
    record_id: str
    field: str
    severity: str   # error | warning
    message: str


def _blank(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or str(v).strip() == ""


def validate_record(rec: dict, today: date | None = None) -> list[Issue]:
    today = today or datetime.now(timezone.utc).date()
    rid = str(rec.get("record_id") or rec.get("title") or "?")[:60]
    out: list[Issue] = []
    err = lambda f, m: out.append(Issue(rid, f, "error", m))
    warn = lambda f, m: out.append(Issue(rid, f, "warning", m))

    for f in S.REQUIRED_NONEMPTY:
        if _blank(rec.get(f)):
            err(f, "required field is empty")

    rtype = rec.get("record_type")
    if rtype not in S.RECORD_TYPES:
        err("record_type", f"must be one of {S.RECORD_TYPES}")

    state = rec.get("state")
    if not _blank(state):
        if state == S.NATIONAL:
            if rtype != "activity" or rec.get("geographic_scope") != "national":
                err("state", "'India (national)' is only allowed for national-scope activities")
        elif state == S.PAN_INDIA:
            if rtype != "opportunity":
                err("state", "'Pan-India' is only allowed for opportunities")
        elif state not in REGION_BY_NAME:
            err("state", f"{state!r} is not a canonical state/UT name")
        else:
            reg = REGION_BY_NAME[state]
            if rec.get("state_code") != reg.code:
                err("state_code", f"expected {reg.code} for {state}")
            if rec.get("state_type") != reg.kind:
                err("state_type", f"expected {reg.kind} for {state}")

    if rec.get("category") not in S.CATEGORIES:
        err("category", f"unknown category {rec.get('category')!r}")
    if rec.get("sector") not in S.SECTORS:
        err("sector", f"unknown sector {rec.get('sector')!r}")
    if rec.get("source_type") not in S.SOURCE_TYPES:
        err("source_type", f"unknown source_type {rec.get('source_type')!r}")
    if rec.get("verification_status") not in S.VERIFICATION_STATUSES:
        err("verification_status", f"unknown status {rec.get('verification_status')!r}")

    if rec.get("summary_basis") not in S.SUMMARY_BASES:
        err("summary_basis", f"must be one of {S.SUMMARY_BASES}")
    if rec.get("url_type") not in S.URL_TYPES:
        err("url_type", f"must be one of {S.URL_TYPES}")
    elif "news.google.com" in str(rec.get("source_url") or "") and rec.get("url_type") != "google_news_redirect":
        err("url_type", "news.google.com link must be labelled google_news_redirect")
    ds = [x for x in str(rec.get("discovery_sources") or "").split("|") if x]
    if not ds or any(x not in S.DISCOVERY_SOURCES for x in ds):
        err("discovery_sources", f"must be '|'-separated values from {S.DISCOVERY_SOURCES}")

    if rec.get("geographic_scope") not in S.GEOGRAPHIC_SCOPES:
        err("geographic_scope", f"must be one of {S.GEOGRAPHIC_SCOPES}")
    if rec.get("location_basis") not in S.LOCATION_BASES:
        err("location_basis", f"must be one of {S.LOCATION_BASES}")
    if rec.get("activity_stage") not in S.ACTIVITY_STAGES:
        err("activity_stage", f"must be one of {S.ACTIVITY_STAGES}")
    elif rec.get("activity_stage") != "undetermined" and _blank(rec.get("stage_confidence")):
        err("stage_confidence", "a determined stage must state its confidence")
    if rec.get("stage_cue") not in S.STAGE_CUES:
        err("stage_cue", f"must be one of {S.STAGE_CUES}")

    # URL sanity
    url = rec.get("source_url")
    if not _blank(url):
        u = urlparse(str(url))
        if u.scheme not in ("http", "https") or not u.netloc:
            err("source_url", "not an absolute http(s) URL")

    # Dates: published_date may be missing but then precision must say 'unknown'.
    pd_, prec = rec.get("published_date"), rec.get("date_precision")
    if prec not in S.DATE_PRECISIONS:
        err("date_precision", f"must be one of {S.DATE_PRECISIONS}")
    if _blank(pd_):
        if prec != "unknown":
            err("published_date", "missing date must carry date_precision='unknown'")
        warn("published_date", "no publication date available")
    else:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(pd_)):
            err("published_date", "must be ISO YYYY-MM-DD")
        elif date.fromisoformat(str(pd_)) > today:
            err("published_date", "date is in the future")
        elif prec == "unknown":
            err("date_precision", "a date is present but precision says 'unknown'")
    ad, ads = rec.get("announcement_date"), rec.get("announcement_date_status")
    if ads not in S.ANNOUNCEMENT_DATE_STATUSES:
        err("announcement_date_status", f"must be one of {S.ANNOUNCEMENT_DATE_STATUSES}")
    if ads == "not_determined" and not _blank(ad):
        err("announcement_date", "status is 'not_determined' but a date is set")
    if ads == "stated" and _blank(ad):
        err("announcement_date", "status is 'stated' but no date is set")

    # Geography
    lat, lon = rec.get("lat"), rec.get("lon")
    gp = rec.get("geo_precision")
    if gp not in S.GEO_PRECISIONS:
        err("geo_precision", f"must be one of {S.GEO_PRECISIONS}")
    if not _blank(lat) or not _blank(lon):
        try:
            la, lo = float(lat), float(lon)
            if not (INDIA_BBOX[0] <= la <= INDIA_BBOX[1] and INDIA_BBOX[2] <= lo <= INDIA_BBOX[3]):
                err("lat", "coordinates outside India bounding box")
        except (TypeError, ValueError):
            err("lat", "non-numeric coordinates")
        if gp == "none":
            err("geo_precision", "coordinates present but precision is 'none'")
    elif gp in ("institution", "city"):
        err("geo_precision", f"precision is {gp!r} but no coordinates")

    # Integrity of provenance claims
    vs, st = rec.get("verification_status"), rec.get("source_type")
    if vs == "primary_source" and st not in ("government", "academic"):
        err("verification_status", "'primary_source' requires a government/academic publisher")
    if vs == "corroborated":
        others = [x for x in str(rec.get("corroborating_sources") or "").split("|") if x]
        if len(others) < 1:
            err("verification_status", "'corroborated' requires at least one other publisher")
    if _blank(rec.get("verification_basis")):
        err("verification_basis", "every status must carry its basis")

    if rtype == "opportunity":
        if rec.get("opportunity_type") not in S.OPPORTUNITY_TYPES:
            err("opportunity_type", f"must be one of {S.OPPORTUNITY_TYPES}")
        if rec.get("deadline_status") not in ("stated", "not_stated"):
            err("deadline_status", "must be stated|not_stated")
        if rec.get("review_status") not in S.REVIEW_STATUSES:
            err("review_status", f"must be one of {S.REVIEW_STATUSES}")
        if rec.get("deadline_status") == "not_stated" and not _blank(rec.get("deadline")):
            err("deadline", "deadline set although status is not_stated")
    return out


def validate_records(records: list[dict], today: date | None = None) -> tuple[list[dict], list[dict], list[Issue]]:
    """Split into (valid, rejected_with_reason, all_issues). Also flags duplicate record_ids."""
    valid, rejected, issues, seen = [], [], [], set()
    for r in records:
        iss = validate_record(r, today)
        rid = r.get("record_id")
        if rid in seen:
            iss.append(Issue(str(rid), "record_id", "error", "duplicate record_id"))
        seen.add(rid)
        issues.extend(iss)
        errs = [i for i in iss if i.severity == "error"]
        if errs:
            rejected.append({**r, "exclusion_reason": "validation_failed: " + "; ".join(f"{i.field}: {i.message}" for i in errs)})
        else:
            valid.append(r)
    return valid, rejected, issues
