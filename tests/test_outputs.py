"""Consistency of the published outputs: counts in run_summary.json, the CSVs and the XLSX
must agree, and provenance labels must be internally consistent. Skips if not generated."""
import json
from pathlib import Path

import pandas as pd
import pytest

P = Path(__file__).resolve().parent.parent / "data" / "processed"
pytestmark = pytest.mark.skipif(not (P / "run_summary.json").exists(), reason="run the pipeline first")


@pytest.fixture(scope="module")
def out():
    return {"summary": json.loads((P / "run_summary.json").read_text()),
            "a": pd.read_csv(P / "activities.csv", dtype=str, keep_default_na=False),
            "o": pd.read_csv(P / "opportunities.csv", dtype=str, keep_default_na=False),
            "x": pd.read_excel(P / "ai_policy_activity.xlsx", sheet_name=None, dtype=str)}


def test_counts_agree_across_summary_csv_and_xlsx(out):
    s = out["summary"]
    assert len(out["a"]) == s["published_activities"] == len(out["x"]["activities"])
    assert len(out["o"]) == s["published_opportunities"] == len(out["x"]["opportunities"])


def test_provenance_labels_are_consistent(out):
    for df in (out["a"], out["o"]):
        redirect = df["source_url"].str.contains("news.google.com")
        assert (df.loc[redirect, "url_type"] == "google_news_redirect").all()
        assert (df.loc[~redirect, "url_type"] == "publisher_direct").all()
        # a headline-only record must not carry a description pretending to be a summary
        ho = df["summary_basis"] == "headline_only"
        assert (df.loc[ho, "summary"] == df.loc[ho, "title"]).all()
        assert (df["announcement_date_status"] == "not_determined").all()
        assert df["record_id"].is_unique
