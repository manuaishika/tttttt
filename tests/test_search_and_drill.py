"""Search, filter and drill-down behaviour against the REAL dataset (headless AppTest).
Expected counts are computed independently with pandas and compared with what the app shows."""
import re
from pathlib import Path

import pandas as pd
import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
from dashboard.data import load_all, search_mask  # noqa: E402
from dashboard.ui import deadline_display  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")
D = load_all()
ALL = pd.concat([D["activities"], D["national"]], ignore_index=True)


def shown(**state):
    at = st_testing.AppTest.from_file(APP, default_timeout=90)
    at.session_state["init"] = True
    at.session_state["nav"] = "Activity Explorer"
    at.session_state["focus_state"] = "—"
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, at.exception
    html = " ".join(m.value for m in at.markdown)
    total = int(re.search(r'<div class="v">([\d,]+)</div><div class="l">matching records across India', html).group(1).replace(",", ""))
    states = int(re.search(r'<div class="v">(\d+) of 36</div>', html).group(1))
    return total, states, html


def expected(q="", states=None):
    R = ALL[search_mask(ALL, q)]
    if states:
        R = R[R["state"].isin(states)]
    return len(R), R.loc[R["state"] != "India (national)", "state"].nunique(), R


def test_global_search_collab_spans_india_without_a_state():
    n, k, R = expected("collab")
    assert n > 0 and k > 1                       # not restricted to one state
    assert shown(ax_q="collab")[:2] == (n, k)


@pytest.mark.parametrize("q", ["IIT Madras", "responsible AI", "Kerala"])
def test_institution_safety_term_and_state_name(q):
    n, k, _ = expected(q)
    assert n > 0 and shown(ax_q=q)[:2] == (n, k)


def test_two_states_narrow_and_clearing_restores_national_results():
    n_all, k_all, R_all = expected("collab")
    n2, k2, _ = expected("collab", ["Kerala", "Karnataka"])
    assert shown(ax_q="collab", ax_states=["Kerala", "Karnataka"])[:2] == (n2, k2) and n2 < n_all
    n1, _, _ = expected("collab", ["Karnataka"])
    assert shown(ax_q="collab", ax_states=["Karnataka"])[0] == n1
    assert shown(ax_q="collab", ax_states=[])[:2] == (n_all, k_all)       # state cleared -> national view back


def test_national_records_discoverable_in_global_search():
    n, _, R = expected("TRAI")
    assert n > 0 and (R["geographic_scope"] == "national").any()
    assert shown(ax_q="TRAI")[0] == n


def test_clear_all_returns_full_dataset_and_empty_state_is_explained():
    assert shown()[0] == len(ALL)
    _, _, html = shown(ax_q="zzzz-no-such-term")
    assert "not</b> that no AI activity exists" in html


def test_drill_filters_match_independent_counts():
    # what a click on the 'Kerala · AI policy and governance' bar sets
    R = ALL[(ALL["state"] == "Kerala") & (ALL["category"] == "policy_governance")]
    assert shown(ax_states=["Kerala"], ax_cats=["policy_governance"],
                 drill={"label": "test", "origin": "State Intelligence", "restore": {}})[0] == len(R)


# ---- deadline wording ----
def _r(**kw):
    base = {"deadline_extraction_status": "not_checked", "app_deadline_dt": pd.NaT, "deadline_dt": pd.NaT,
            "deadline_confidence": "", "deadline_evidence": ""}
    base.update(kw)
    return pd.Series(base)


ASOF = pd.Timestamp("2026-11-20")


def test_extracted_deadline_shows_date_and_evidence():
    t, ev = deadline_display(_r(deadline_extraction_status="extracted", app_deadline_dt=pd.Timestamp("2026-11-29"),
                                deadline_confidence="high", deadline_evidence="The last date ... November 29, 2026."), ASOF)
    assert "29 Nov 2026" in t and "had not yet passed" in t and ev


def test_inaccessible_source_is_never_called_not_stated():
    t, _ = deadline_display(_r(deadline_extraction_status="source_inaccessible"), ASOF)
    assert "not verified" in t and "not stated" not in t.lower()
    t, _ = deadline_display(_r(deadline_extraction_status="source_restricted"), ASOF)
    assert "robots.txt" in t


def test_conflict_and_read_but_absent_are_labelled():
    assert "Conflicting" in deadline_display(_r(deadline_extraction_status="conflict"), ASOF)[0]
    assert "No application deadline found" in deadline_display(_r(deadline_extraction_status="not_stated_in_accessible_sources"), ASOF)[0]


def test_real_iit_roorkee_record():
    o = D["opportunities"]
    r = o[o["title"].str.contains("IIT Roorkee")].iloc[0]
    assert r["application_deadline"] == "2026-11-29" and "November 29, 2026" in r["deadline_evidence"]
