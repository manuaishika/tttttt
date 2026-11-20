"""Data access for the dashboard: reads ONLY the pipeline's processed outputs.

Defensive by design: missing files give empty frames (the app shows a notice instead of
crashing), unparseable dates become NaT, blank URLs become None (rendered as "no link"),
and the state-boundary asset is validated before use (else the map falls back to points).
"""
from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src import schema as S                     # noqa: E402
from src.reference import REGIONS               # noqa: E402
from src.stage import STAGES                    # noqa: E402

PROCESSED = ROOT / "data" / "processed"
GEOJSON = ROOT / "dashboard" / "assets" / "india_states.geojson"

CATEGORY_LABELS = S.CATEGORIES
CATEGORY_ORDER = list(S.CATEGORIES)
SECTOR_LABELS = S.SECTORS
STAGE_LABELS = STAGES
STAGE_ORDER = list(STAGES)
VERIFICATION_LABELS = {
    "primary_source": "Primary source",
    "corroborated": "Corroborated (2+ publishers)",
    "single_secondary_source": "Single secondary source",
    "unverified": "Unverified",
}
VERIFICATION_ORDER = list(VERIFICATION_LABELS)
SOURCE_TYPE_LABELS = {"government": "Government", "academic": "Academic", "think_tank": "Think tank",
                      "established_media": "Established media", "other_media": "Unclassified publisher"}
URL_TYPE_LABELS = {"publisher_direct": "Direct publisher link", "google_news_redirect": "Google News redirect"}
DISCOVERY_LABELS = {"google_news_rss": "Google News RSS", "direct_feed": "Direct RSS feed", "gnews": "GNews API",
                    "newsapi": "NewsAPI"}
EVIDENCE_LABELS = {"documented_activity": "Documented activity in this collection",
                   "limited_evidence": "Limited evidence in this collection",
                   "no_evidence_found_in_research": "No evidence found in this collection"}
REVIEW_LABELS = {"valid": "Reviewed: genuine opportunity", "borderline": "Reviewed: borderline",
                 "not_an_opportunity": "Reviewed: not an opportunity", "not_reviewed": "Not yet reviewed"}
REGION_NAMES = [r.name for r in REGIONS]
REGION_KIND = {r.name: r.kind for r in REGIONS}
REGION_POINT = {r.name: (r.lat, r.lon) for r in REGIONS}

TEXT_COLS = ["state", "city", "institutions", "title", "summary", "summary_basis", "source_description", "category",
             "sector", "source_name", "source_url", "url_type", "publisher_url", "source_type", "verification_status",
             "verification_basis", "corroborating_sources", "discovery_sources", "state_evidence", "date_precision",
             "announcement_date_status", "opportunity_type", "deadline_status", "record_id", "cluster_id", "raw_ref",
             "collected_at", "category_confidence", "stage_cue", "review_status", "review_note", "matched_query"]


def _read(name: str) -> pd.DataFrame:
    p = PROCESSED / name
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Column as a Series even when the file predates it (empty strings)."""
    return df[name] if name in df else pd.Series("", index=df.index)


def clean_records(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    for c in TEXT_COLS:
        if c not in df:
            df[c] = ""                               # older files may predate a column
        df[c] = df[c].fillna("").astype(str).str.strip()
    df["published"] = pd.to_datetime(_col(df, "published_date"), errors="coerce", format="%Y-%m-%d")
    df["deadline_dt"] = pd.to_datetime(_col(df, "deadline"), errors="coerce", format="%Y-%m-%d")
    for c in ("lat", "lon"):
        df[c] = pd.to_numeric(_col(df, c), errors="coerce")
    df["duplicate_count"] = pd.to_numeric(_col(df, "duplicate_count"), errors="coerce").fillna(1).astype(int)
    df["link"] = df["source_url"].where(df["source_url"].str.match(r"^https?://"), None)
    df["category_label"] = df["category"].map(CATEGORY_LABELS).fillna("Uncategorised")
    df["sector_label"] = df["sector"].map(SECTOR_LABELS).fillna("Not sector-specific")
    df["verification_label"] = df["verification_status"].map(VERIFICATION_LABELS).fillna("Unverified")
    df["source_type_label"] = df["source_type"].map(SOURCE_TYPE_LABELS).fillna("Unclassified publisher")
    df["url_type"] = df["url_type"].where(df["url_type"] != "", df["source_url"].map(
        lambda u: "google_news_redirect" if "news.google.com" in u else "publisher_direct"))
    df["url_label"] = df["url_type"].map(URL_TYPE_LABELS)
    df["stage_cue"] = df["stage_cue"].where(df["stage_cue"] != "", "unclear")
    df["stage_label"] = df["stage_cue"].map(STAGE_LABELS).fillna("Stage unclear")
    df["discovery_label"] = df["discovery_sources"].map(
        lambda s: ", ".join(DISCOVERY_LABELS.get(x, x) for x in s.split("|") if x) or "—")
    # A headline is not a summary: only publisher-supplied text is shown as a description.
    has_desc = df["summary_basis"] == "publisher_description"
    df["description_full"] = df["source_description"].where(has_desc & (df["source_description"] != ""), df["summary"])
    df["description_full"] = df["description_full"].where(has_desc, "")
    df["strong_evidence"] = df["verification_status"].isin(["primary_source", "corroborated"])
    df["search_text"] = (df["title"] + " \n " + df["description_full"] + " \n " + df["state"] + " \n " + df["city"]
                         + " \n " + df["institutions"].str.replace("|", " ", regex=False) + " \n " + df["category_label"]
                         + " \n " + df["sector_label"] + " \n " + df["source_name"] + " \n " + df["stage_label"]
                         + " \n " + df["opportunity_type"].str.replace("_", " ")).str.casefold()
    return df


def parse_query(q: str) -> list[str]:
    """Split a search query into terms; "quoted phrases" stay together. Unbalanced quotes
    fall back to whitespace splitting rather than failing."""
    q = (q or "").strip()
    if not q:
        return []
    try:
        parts = shlex.split(q)
    except ValueError:
        parts = q.replace('"', " ").split()
    return [p.casefold() for p in parts if p.strip()]


def search_mask(df: pd.DataFrame, q: str) -> pd.Series:
    """Every term must appear (AND), case-insensitive, anywhere in the record's searchable
    fields. Terms match inside words ('gov' matches 'government')."""
    terms = parse_query(q)
    if df.empty or not terms:
        return pd.Series(True, index=df.index)
    m = pd.Series(True, index=df.index)
    for t in terms:
        m &= df["search_text"].str.contains(re.escape(t), regex=True)
    return m


def load_all() -> dict:
    acts = clean_records(_read("activities.csv"))
    opps = clean_records(_read("opportunities.csv"))
    summary = {}
    if (PROCESSED / "run_summary.json").exists():
        summary = json.loads((PROCESSED / "run_summary.json").read_text())
    return {"activities": acts, "opportunities": opps, "coverage": _read("state_coverage.csv"),
            "registry": _read("source_registry.csv"), "duplicates": _read("duplicates.csv"),
            "summary": summary, "geojson": load_geojson()}


def load_geojson() -> dict | None:
    """Return the boundary GeoJSON only if it covers exactly our 36 canonical regions."""
    try:
        gj = json.loads(GEOJSON.read_text())
        names = {f["properties"]["state"] for f in gj["features"]}
        return gj if names == set(REGION_NAMES) else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def file_bytes(name: str) -> bytes | None:
    p = PROCESSED / name
    return p.read_bytes() if p.exists() else None
