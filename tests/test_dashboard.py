"""Dashboard tests on the real processed data: every section renders, state focus works,
search behaves as documented, and the record detail view shows provenance."""
from pathlib import Path

import pandas as pd
import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
APP = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")
SECTIONS = ["Overview", "State Intelligence", "Activity Explorer", "Opportunities", "Methodology"]


def _run(**state):
    at = st_testing.AppTest.from_file(APP, default_timeout=90)
    for k, v in state.items():
        at.session_state[k] = v
    return at.run()


@pytest.mark.parametrize("section", SECTIONS)
def test_each_section_renders(section):
    at = _run(init=True, nav=section, focus_state="—")
    assert not at.exception, at.exception


@pytest.mark.parametrize("section", ["Overview", "State Intelligence"])
def test_state_focus_renders_profile(section):
    at = _run(init=True, nav=section, focus_state="Karnataka")
    assert not at.exception
    assert any("Karnataka" in m.value for m in at.markdown)


def test_state_with_no_records_says_so_without_inferring_absence():
    at = _run(init=True, nav="Overview", focus_state="Lakshadweep")
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "not an absence of activity" in text


def test_explorer_search_with_no_results_is_handled():
    at = _run(init=True, nav="Activity Explorer", focus_state="—")
    at.text_input(key="ax_q").input("zzzz-no-such-term").run()
    assert not at.exception
    assert any("0 of" in m.value for m in at.markdown)


# ---- search semantics (pure function) ----
from dashboard.data import clean_records, parse_query, search_mask  # noqa: E402


def _df():
    return clean_records(pd.DataFrame([
        {"record_id": "a", "title": "Kerala cabinet approves AI mission", "state": "Kerala", "category": "policy_governance",
         "sector": "none", "summary_basis": "headline_only", "summary": "Kerala cabinet approves AI mission",
         "source_name": "The Hindu", "source_url": "https://x/a", "institutions": "", "stage_cue": "announced_or_approved"},
        {"record_id": "b", "title": "IIT Madras launches centre of excellence", "state": "Tamil Nadu",
         "category": "research_institutions", "sector": "healthcare", "summary_basis": "publisher_description",
         "summary": "x", "source_description": "The centre will study AI in hospitals.", "source_name": "NDTV",
         "source_url": "https://news.google.com/rss/articles/x", "institutions": "IIT Madras", "stage_cue": "unclear"},
    ]))


def test_parse_query_keeps_quoted_phrases_and_survives_bad_quotes():
    assert parse_query('"centre of excellence" IIT') == ["centre of excellence", "iit"]
    assert parse_query('"unbalanced quote') == ["unbalanced", "quote"]
    assert parse_query("   ") == []


def test_search_is_and_across_fields():
    df = _df()
    assert search_mask(df, "kerala mission").tolist() == [True, False]          # words in any order
    assert search_mask(df, "hospitals").tolist() == [False, True]               # publisher description searched
    assert search_mask(df, "healthcare madras").tolist() == [False, True]       # sector + institution
    assert search_mask(df, "research institutional").tolist() == [False, True]  # category label
    assert search_mask(df, "kerala hospitals").tolist() == [False, False]       # AND, not OR
    assert search_mask(df, "").all()


def test_headline_only_records_have_no_description():
    df = _df()
    assert df.loc[0, "description_full"] == ""
    assert df.loc[1, "description_full"].startswith("The centre")
    assert df.loc[1, "url_label"] == "Google News redirect"
