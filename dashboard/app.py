"""India AI Policy & Ecosystem Intelligence - Streamlit app.

    streamlit run dashboard/app.py

Five sections: Overview, State Intelligence, Activity Explorer, Opportunities, Methodology.
Reads only data/processed/* produced by `python -m src.pipeline`. Nothing here creates,
scores or rewrites records; it filters and displays them with their provenance.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dashboard.data import (CATEGORY_LABELS, CATEGORY_ORDER, DISCOVERY_LABELS, EVIDENCE_LABELS,  # noqa: E402
                            REGION_KIND, REGION_NAMES, REVIEW_LABELS, SECTOR_LABELS, SOURCE_TYPE_LABELS,
                            STAGE_LABELS, STAGE_ORDER, URL_TYPE_LABELS, VERIFICATION_LABELS, VERIFICATION_ORDER,
                            file_bytes, load_all, search_mask)
from dashboard.ui import (BLUE, CSS, INK2, MAP_METRICS, RULE, build_map, category_table_html, esc,  # noqa: E402
                          hbar, hotspots, record_browser, record_row_html, render_detail, select_callback,
                          state_metrics, stats_html)

st.set_page_config(page_title="India AI Policy & Ecosystem Intelligence", page_icon="🗺️", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)

SECTIONS = ["Overview", "State Intelligence", "Activity Explorer", "Opportunities", "Methodology"]
NONE = "—"


@st.cache_data(show_spinner=False)
def get_data(_stamp: float) -> dict:
    return load_all()


def _stamp() -> float:
    p = Path(__file__).resolve().parent.parent / "data" / "processed" / "activities.csv"
    return p.stat().st_mtime if p.exists() else 0.0


D = get_data(_stamp())
ACTS, OPPS, COV, REG, DUPS, SUMMARY, GEO = (D["activities"], D["opportunities"], D["coverage"], D["registry"],
                                            D["duplicates"], D["summary"], D["geojson"])
COLLECTED = SUMMARY.get("run_date", "unknown")

# ------------------------------------------------------------------ state & deep links
ss = st.session_state
if "init" not in ss:
    qp = st.query_params
    ss.nav = qp.get("section") if qp.get("section") in SECTIONS else "Overview"
    ss.focus_state = qp.get("state") if qp.get("state") in REGION_NAMES else NONE
    ss.init = True
ss.setdefault("focus_state", NONE)
ss.setdefault("nav", "Overview")


def keep_nav() -> None:
    """Clicking the active section deselects it in a segmented control; keep the last one."""
    if ss.nav is None:
        ss.nav = ss.get("_last_nav", "Overview")
    ss._last_nav = ss.nav


def go_to(section: str, state: str | None = None) -> None:
    ss.nav = section
    if state is not None:
        ss.focus_state = state


def set_focus_from(widget_key: str) -> None:
    ss.focus_state = ss[widget_key]


# ------------------------------------------------------------------ header + navigation
h1, h2 = st.columns([1, 1.25], vertical_alignment="bottom")
with h1:
    st.markdown('<div class="eyebrow">India · AI policy & ecosystem</div>', unsafe_allow_html=True)
    st.markdown("# India AI Policy & Ecosystem Intelligence")
with h2:
    st.segmented_control("Section", SECTIONS, key="nav", label_visibility="collapsed", on_change=keep_nav)
section = ss.nav or "Overview"
st.markdown('<div class="rule" style="margin-top:0.6rem"></div>', unsafe_allow_html=True)

if ACTS.empty:
    st.warning("No processed data found. Run `python -m src.pipeline` first (see README).")
    st.stop()


def state_summary(name: str) -> dict:
    sub = ACTS[ACTS["state"] == name]
    crow = COV[COV["state"] == name].iloc[0] if not COV.empty and (COV["state"] == name).any() else None
    return {"sub": sub, "crow": crow, "n": len(sub), "pubs": sub["source_name"].nunique(),
            "strong": int(sub["strong_evidence"].sum()),
            "status": EVIDENCE_LABELS.get(crow["evidence_status"], "—") if crow is not None else "—",
            "retrieved": int(crow["raw_items_retrieved_for_state_queries"]) if crow is not None else 0}


# ================================================================== OVERVIEW
def overview() -> None:
    st.markdown('<p class="lede">Where AI is being governed, deployed, researched, funded and taught across India\'s '
                '28 states and 8 union territories, as documented in public news and official feeds. '
                f'Every record carries its source and evidence status. Collected {esc(COLLECTED)}.</p>',
                unsafe_allow_html=True)
    map_col, side = st.columns([1.7, 1], gap="large")
    with map_col:
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        metric = c1.radio("Map shows", list(MAP_METRICS), format_func=lambda k: MAP_METRICS[k][0], horizontal=True,
                          key="ov_metric")
        show_hot = c2.toggle("Institutions", value=True, key="ov_hot",
                             help="White markers: institutions and cities named in records, placed only from the "
                                  "project's institution/city registry. Other records are shown at state level only.")
        focus = ss.focus_state if ss.focus_state in REGION_NAMES else None
        map_key = f"ov_map_{focus or 'none'}"   # new key on focus change: the chart's own selection resets cleanly
        fig = build_map(metric, state_metrics(ACTS), focus, GEO, hotspots(ACTS) if show_hot else None)
        st.plotly_chart(fig, use_container_width=True, key=map_key, on_select=select_callback(map_key),
                        selection_mode="points", config={"displayModeBar": False, "scrollZoom": False})
        st.markdown(f'<div class="note"><b>{esc(MAP_METRICS[metric][0])}.</b> {esc(MAP_METRICS[metric][2])} '
                    'Grey means no records were found in this collection, which is not evidence that no activity exists. '
                    + ('Boundaries: community dataset (pinned, checksum-verified) showing India\'s official external '
                       'boundary; not an authoritative Survey of India product.' if GEO else
                       'Boundary file unavailable: states are shown as approximate points.') + '</div>',
                    unsafe_allow_html=True)
    with side:
        options = [NONE] + REGION_NAMES
        ss["ov_state"] = ss.focus_state if ss.focus_state in options else NONE
        st.selectbox("State / UT", options, key="ov_state", on_change=set_focus_from, args=("ov_state",),
                     format_func=lambda s: "Click the map or choose a state…" if s == NONE else s)
        if ss.focus_state in REGION_NAMES:
            state_panel(ss.focus_state)
        else:
            national_panel()

    st.markdown("<h2>National picture</h2>", unsafe_allow_html=True)
    strong = int(ACTS["strong_evidence"].sum())
    valid_opps = int((OPPS["review_status"] == "valid").sum()) if not OPPS.empty else 0
    dmin, dmax = ACTS["published"].min(), ACTS["published"].max()
    st.markdown(stats_html([
        (f"{len(ACTS):,}", "activity records (distinct, after merging duplicate reports)"),
        (f"{ACTS.loc[ACTS['state'].isin(REGION_NAMES), 'state'].nunique()} of 36", "states and UTs with at least one record"),
        (f"{strong:,} ({strong / len(ACTS):.0%})", "well-sourced: primary source or 2+ publishers"),
        (f"{valid_opps} of {len(OPPS)}", "opportunities reviewed as genuine"),
        (f"{dmin:%b %Y} – {dmax:%b %Y}" if pd.notna(dmin) else "—", "publication window of sources"),
    ]), unsafe_allow_html=True)
    st.write("")
    a, b = st.columns([1, 1.15], gap="large")
    with a:
        st.markdown("<h3>What was found, by category</h3>", unsafe_allow_html=True)
        counts = ACTS["category"].value_counts().reindex(CATEGORY_ORDER).fillna(0).astype(int)
        st.plotly_chart(hbar([CATEGORY_LABELS[c] for c in counts.index], counts.tolist(), 300, "records", len(ACTS)),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="muted">Number of records per category (share of all records). Each record has one '
                    'primary category assigned by transparent keyword rules.</div>', unsafe_allow_html=True)
    with b:
        st.markdown("<h3>Latest well-sourced developments</h3>", unsafe_allow_html=True)
        st.markdown('<div class="muted">Most recent records published by an official source or reported by two or '
                    'more publishers.</div>', unsafe_allow_html=True)
        latest = ACTS[ACTS["strong_evidence"]].sort_values(["published", "duplicate_count"], ascending=False).head(6)
        st.markdown("".join(record_row_html(r) for _, r in latest.iterrows()), unsafe_allow_html=True)
        st.button("Explore all activities →", on_click=go_to, args=("Activity Explorer",))


def state_panel(name: str) -> None:
    s = state_summary(name)
    st.markdown(f'<div class="eyebrow" style="margin-top:0.6rem">{esc(REGION_KIND[name])}</div>'
                f'<h2 style="margin-top:0.1rem !important">{esc(name)}</h2>', unsafe_allow_html=True)
    if s["n"] == 0:
        st.markdown(f'<div class="note">No records were found for {esc(name)} in this collection '
                    f'({s["retrieved"]} items retrieved by the discovery queries were screened). This reflects the '
                    'sources searched, not an absence of activity.</div>', unsafe_allow_html=True)
        return
    st.markdown(f'<p class="lede"><b>{s["n"]}</b> activities found from <b>{s["pubs"]}</b> publishers; '
                f'<b>{s["strong"]}</b> well-sourced. <span class="muted">{esc(s["status"])}.</span></p>',
                unsafe_allow_html=True)
    sub = s["sub"]
    rows = "".join(
        f"<tr><td>{esc(CATEGORY_LABELS[c])}</td>"
        + (f"<td class='n'>{int((sub['category'] == c).sum())}</td>" if (sub['category'] == c).any()
           else "<td class='n none'>none found</td>") + "</tr>" for c in CATEGORY_ORDER)
    st.markdown(f"<table class='tbl'>{rows}</table>", unsafe_allow_html=True)
    insts = sub["institutions"].str.split("|").explode()
    insts = insts[insts != ""].value_counts()
    if not insts.empty:
        st.markdown('<div class="muted" style="margin-top:0.6rem">Institutions named: '
                    + esc(", ".join(f"{i} ({n})" for i, n in insts.head(5).items())) + "</div>", unsafe_allow_html=True)
    st.markdown('<h3 style="margin-top:0.8rem">Latest</h3>', unsafe_allow_html=True)
    st.markdown("".join(record_row_html(r, show_state=False)
                        for _, r in sub.sort_values("published", ascending=False).head(3).iterrows()),
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.button("Full state profile →", on_click=go_to, args=("State Intelligence",), type="primary",
              use_container_width=True)
    c2.button("Clear selection", on_click=go_to, args=("Overview", NONE), use_container_width=True)


def national_panel() -> None:
    st.markdown('<h3 style="margin-top:0.6rem">Reporting volume by state</h3>', unsafe_allow_html=True)
    st.markdown('<div class="muted">Records found per state/UT in this collection. This is reporting volume in '
                'English-language sources, not a ranking of AI activity or capability.</div>', unsafe_allow_html=True)
    m = state_metrics(ACTS).sort_values("records", ascending=False)
    rows = "".join(f"<tr><td>{esc(r.state)}</td><td class='n'>{r.records}</td><td class='n'>{r.categories}/6</td>"
                   f"<td class='n'>{r.strong}</td></tr>" for r in m.head(12).itertuples())
    st.markdown("<table class='tbl'><tr><th>State / UT</th><th class='n'>Records</th><th class='n'>Categories</th>"
                f"<th class='n'>Well-sourced</th></tr>{rows}</table>", unsafe_allow_html=True)
    zero = m[m["records"] == 0]["state"].tolist()
    st.markdown(f'<div class="muted" style="margin-top:0.5rem">Showing 12 of 36. No records found in this collection: '
                f'{esc(", ".join(zero) or "none")}.</div>', unsafe_allow_html=True)


# ================================================================== STATE INTELLIGENCE
def state_intelligence() -> None:
    options = [NONE] + REGION_NAMES
    ss["si_state"] = ss.focus_state if ss.focus_state in options else NONE
    c1, _ = st.columns([1, 2])
    c1.selectbox("State / UT", options, key="si_state", on_change=set_focus_from, args=("si_state",),
                 format_func=lambda s: "Choose a state or UT…" if s == NONE else s)
    name = ss.focus_state
    if name not in REGION_NAMES:
        st.markdown('<p class="lede">Choose a state or UT to see what was found: activities by area, how far each has '
                    'progressed according to its headline, named institutions and the sources behind them. You can '
                    'also select a row below.</p>', unsafe_allow_html=True)
        cov = COV.copy()
        cov["Evidence (this collection)"] = cov["evidence_status"].map(EVIDENCE_LABELS)
        tbl = cov[["state", "state_type", "records", "categories_covered", "primary_source_records",
                   "corroborated_records", "raw_items_retrieved_for_state_queries", "Evidence (this collection)"]]
        ev = st.dataframe(tbl.rename(columns={"state": "State / UT", "state_type": "Type", "records": "Records",
                                              "categories_covered": "Categories", "primary_source_records": "Primary",
                                              "corroborated_records": "Corroborated",
                                              "raw_items_retrieved_for_state_queries": "Items screened"}),
                          hide_index=True, use_container_width=True, height=560, on_select="rerun",
                          selection_mode="single-row", key="si_table")
        if ev.selection.rows:
            ss.focus_state = tbl.iloc[ev.selection.rows[0]]["state"]
            st.rerun()
        return

    s = state_summary(name)
    sub = s["sub"]
    st.markdown(f'<div class="eyebrow">{esc(REGION_KIND[name])}</div><h1 style="margin-top:0.1rem !important">'
                f'{esc(name)}</h1>', unsafe_allow_html=True)
    st.markdown(stats_html([
        (str(s["n"]), "activities found in this collection"),
        (str(s["pubs"]), "distinct publishers"),
        (str(s["strong"]), "well-sourced (primary or 2+ publishers)"),
        (f'{sub["category"].nunique()}/6', "categories with at least one record"),
        (str(s["retrieved"]), "items screened from this state's discovery queries"),
    ]), unsafe_allow_html=True)
    st.markdown(f'<div class="note"><b>{esc(s["status"])}.</b> Counts describe what English-language reporting in this '
                'collection contains. They do not measure maturity, and a category with no records means nothing was '
                'found here, not that nothing exists.</div>', unsafe_allow_html=True)
    if sub.empty:
        return

    st.markdown("<h2>Activity by area</h2>", unsafe_allow_html=True)
    st.markdown('<div class="muted">Stage columns read the headline\'s wording (e.g. "plans to", "approves", '
                '"rolls out"). They separate proposals from announcements from things reported as running; they are not '
                'an assessment of progress on the ground.</div>', unsafe_allow_html=True)
    st.markdown(category_table_html(sub), unsafe_allow_html=True)

    st.markdown("<h2>Activities found</h2>", unsafe_allow_html=True)
    present = [c for c in CATEGORY_ORDER if (sub["category"] == c).any()]
    pick = st.segmented_control("Area", present, format_func=CATEGORY_LABELS.get, selection_mode="multi",
                                key=f"si_cat_{name}", label_visibility="collapsed")
    view = sub[sub["category"].isin(pick)] if pick else sub
    record_browser(view, DUPS, key=f"si_rec_{name}", height=430)

    st.markdown("<h2>Institutions and sources</h2>", unsafe_allow_html=True)
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("<h3>Institutions named</h3>", unsafe_allow_html=True)
        rows = []
        for _, r in sub[sub["institutions"] != ""].iterrows():
            for inst in r["institutions"].split("|"):
                rows.append((inst, r["category_label"]))
        if rows:
            it = pd.DataFrame(rows, columns=["Institution", "Category"])
            agg = it.groupby("Institution").agg(Records=("Category", "size"),
                                                Areas=("Category", lambda s: ", ".join(sorted(set(s))))).reset_index()
            st.dataframe(agg.sort_values("Records", ascending=False), hide_index=True, use_container_width=True)
        else:
            st.markdown('<div class="muted">No institution from the project\'s registry (47 entries: IITs, IISc, IISERs, '
                        'state AI missions and others) is named in these records. Other institutions may appear in the '
                        'headlines themselves.</div>', unsafe_allow_html=True)
    with b:
        st.markdown("<h3>Publishers</h3>", unsafe_allow_html=True)
        src = sub.groupby("source_name").agg(Records=("record_id", "size"), Type=("source_type_label", "first"),
                                             Well_sourced=("strong_evidence", "sum")).reset_index()
        st.dataframe(src.rename(columns={"source_name": "Publisher", "Well_sourced": "Well-sourced"})
                     .sort_values("Records", ascending=False), hide_index=True, use_container_width=True, height=300)
    sectors = sub["sector_label"].value_counts()
    sectors = sectors[sectors.index != "Not sector-specific"]
    if not sectors.empty:
        st.markdown('<div class="muted" style="margin-top:0.6rem">Sectors mentioned: '
                    + esc(", ".join(f"{k} ({v})" for k, v in sectors.items())) + "</div>", unsafe_allow_html=True)


# ================================================================== ACTIVITY EXPLORER
def activity_explorer() -> None:
    st.markdown('<p class="lede">Search and filter all activity records, then select a row to read the full record and '
                'its provenance.</p>', unsafe_allow_html=True)
    q = st.text_input("Search", key="ax_q", placeholder='e.g.  Kerala mission    or    "centre of excellence" IIT',
                      help="All words must match (AND). Case-insensitive; partial words match ('gov' finds "
                           "'government'). Put a phrase in double quotes to match it exactly.")
    st.markdown('<div class="muted">Searches the headline, publisher description (where one exists), state, city, '
                'named institutions, category, sector, stage and publisher. Every word must appear somewhere in the '
                'record.</div>', unsafe_allow_html=True)
    active = sum(bool(ss.get(k)) for k in ("ax_states", "ax_cats", "ax_secs", "ax_ev", "ax_stage", "ax_link"))
    dmin, dmax = ACTS["published"].min().date(), ACTS["published"].max().date()
    active += int(ss.get("ax_dates", (dmin, dmax)) != (dmin, dmax))
    with st.expander(f"Filters · {active} active" if active else "Filters", expanded=False):
        f1, f2, f3 = st.columns(3)
        states = f1.multiselect("State / UT", REGION_NAMES, key="ax_states", placeholder="Any")
        cats = f2.multiselect("Category", CATEGORY_ORDER, format_func=CATEGORY_LABELS.get, key="ax_cats", placeholder="Any")
        secs = f3.multiselect("Sector", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get, key="ax_secs", placeholder="Any")
        f4, f5, f6 = st.columns(3)
        evid = f4.multiselect("Evidence status", VERIFICATION_ORDER, format_func=VERIFICATION_LABELS.get, key="ax_ev",
                              placeholder="Any", help="Support in the sources held. Not a fact-check.")
        stages = f5.multiselect("Stage (headline wording)", STAGE_ORDER, format_func=STAGE_LABELS.get, key="ax_stage",
                                placeholder="Any")
        links = f6.multiselect("Link type", list(URL_TYPE_LABELS), format_func=URL_TYPE_LABELS.get, key="ax_link",
                               placeholder="Any", help="Direct publisher links point to the article. Google News "
                                                       "redirects open it via news.google.com.")
        d1, d2 = st.columns([2, 1], vertical_alignment="bottom")
        dates = d1.slider("Source published between", min_value=dmin, max_value=dmax, value=(dmin, dmax),
                          format="D MMM YYYY", key="ax_dates",
                          help="Publication date of the source, not the date the activity happened.")
        d2.button("Reset search and filters", on_click=reset_explorer, use_container_width=True)
    R = ACTS[search_mask(ACTS, q)]
    for col, vals in (("state", states), ("category", cats), ("sector", secs), ("verification_status", evid),
                      ("stage_cue", stages), ("url_type", links)):
        if vals:
            R = R[R[col].isin(vals)]
    if dates != (dmin, dmax):
        R = R[R["published"].between(pd.Timestamp(dates[0]), pd.Timestamp(dates[1]))]
    st.markdown(f'<h3>{len(R):,} of {len(ACTS):,} records</h3>', unsafe_allow_html=True)
    record_browser(R, DUPS, key="ax_table")
    c1, c2 = st.columns([1, 2])
    c1.download_button("Download these records (CSV)",
                       R.drop(columns=["published", "deadline_dt", "link", "search_text"], errors="ignore")
                       .to_csv(index=False).encode(), "ai_policy_records_filtered.csv", "text/csv")
    with st.expander("Reporting volume over time (matching records)"):
        T = R[R["published"].notna()]
        if T.empty:
            st.info("No dated records match.")
        else:
            monthly = T.groupby(T["published"].dt.to_period("M").dt.to_timestamp()).size()
            fig = go.Figure(go.Bar(x=monthly.index, y=monthly.values, marker=dict(color=BLUE, cornerradius=3),
                                   hovertemplate="%{x|%B %Y}: %{y} records<extra></extra>"))
            fig.update_layout(height=280, margin=dict(l=0, r=0, t=6, b=0), plot_bgcolor="rgba(0,0,0,0)",
                              paper_bgcolor="rgba(0,0,0,0)", bargap=0.3,
                              xaxis=dict(tickformat="%b %Y", tickfont=dict(color=INK2), showgrid=False),
                              yaxis=dict(title=dict(text="Records (by source publication month)",
                                                    font=dict(size=11, color=INK2)), gridcolor=RULE, zeroline=False))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="muted">Counts records by the month their source was published. It reflects '
                        'reporting volume, not when activities happened. News APIs only reach back about 30 days, which '
                        'inflates the latest month slightly; the first and last months are partial.</div>',
                        unsafe_allow_html=True)


def reset_explorer() -> None:
    for k in ("ax_q", "ax_states", "ax_cats", "ax_secs", "ax_ev", "ax_stage", "ax_link", "ax_dates"):
        ss.pop(k, None)


# ================================================================== OPPORTUNITIES
def opportunities() -> None:
    st.markdown('<p class="lede">Fellowships, internships, workshops, hackathons and conferences detected in the '
                'collection. Each entry was manually reviewed and labelled; nothing is hidden, but non-genuine entries '
                'are separated.</p>', unsafe_allow_html=True)
    if OPPS.empty:
        st.info("No opportunity records.")
        return
    counts = OPPS["review_status"].value_counts()
    order = [s for s in ["valid", "borderline", "not_an_opportunity", "not_reviewed"] if s in counts]
    pick = st.segmented_control("Review status", order, default="valid", key="op_status",
                                format_func=lambda s: f"{REVIEW_LABELS[s]} ({counts[s]})",
                                label_visibility="collapsed") or "valid"
    st.markdown(f'<div class="note">Detected automatically (an opportunity type plus a forward-looking cue such as '
                f'"applications open"), then reviewed manually on {esc(COLLECTED)}. Deadlines are shown only when the '
                'source states one, and their status is given <b>as of the collection date</b>; current availability is '
                'not known. Confirm eligibility and dates on the organiser\'s page.</div>', unsafe_allow_html=True)
    asof = pd.Timestamp(COLLECTED) if COLLECTED != "unknown" else None
    V = OPPS[OPPS["review_status"] == pick].sort_values("published", ascending=False)
    for _, r in V.iterrows():
        if pd.notna(r["deadline_dt"]):
            when = f'Deadline {r["deadline_dt"]:%d %b %Y} (stated in source)'
            if asof is not None:
                rel = ("had passed" if r["deadline_dt"] < asof else "fell on" if r["deadline_dt"] == asof
                       else "had not yet passed")
                when += f'; {rel} the collection date ({asof:%d %b %Y})'
        else:
            when = "No deadline stated in the source"
        pub = r["published"].strftime("%d %b %Y") if pd.notna(r["published"]) else "unknown"
        head = (f'<a href="{esc(r["link"])}" target="_blank" rel="noopener">{esc(r["title"])}</a>' if r["link"]
                else f'<span class="t">{esc(r["title"])}</span>')
        desc = f'<div class="d">{esc(r["description_full"][:300])}</div>' if r["description_full"] else ""
        cls = {"valid": "strong", "borderline": "warn", "not_an_opportunity": "bad"}.get(r["review_status"], "")
        st.markdown(
            f'<div class="rec"><span class="tag">{esc(r["opportunity_type"].replace("_", " "))}</span>'
            f'<span class="tag">{esc(r["state"])}</span><span class="tag {cls}">{esc(REVIEW_LABELS[r["review_status"]])}</span>'
            f'<div style="margin-top:0.3rem">{head}</div>{desc}'
            f'<div class="m"><b>{esc(when)}</b> · published {pub} · {esc(r["source_name"])} · '
            f'{esc(r["verification_label"])} · {esc(r["url_label"])}</div>'
            f'<div class="m">Review note: {esc(r["review_note"] or "—")}</div></div>', unsafe_allow_html=True)


# ================================================================== METHODOLOGY
def methodology() -> None:
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        st.markdown("""
## What this collection is
Records of AI-related **policy and government activity** in Indian states and union territories, plus related research,
partnership, deployment, safety and talent activity, collected from public news and official feeds and processed by a
reproducible Python pipeline. It is a research aid for orientation, not an official register or ranking.

## Collection
- **Google News RSS**: the same six themed queries for every one of the 36 states/UTs (policy, deployment, research,
  partnerships/investment, safety/ethics, education/opportunities) plus pan-India opportunity queries, 12-month window.
- **Direct RSS feeds** from PIB and policy-focused publishers (real article URLs and descriptions; recent items only).
- **GNews and NewsAPI** (optional): direct URLs and descriptions; free tiers reach back only ~30 days.
- Official state portals are listed in the source registry but **not scraped**.

Every run is stored as an immutable raw snapshot; processing is deterministic from it. No paywalls are bypassed and no
article pages are fetched.

## Inclusion criteria
A raw item becomes a record only if **all** hold: (1) the headline is about AI ("Air India" excluded); (2) a state/UT is
identifiable from the headline (or, failing that, the publisher description) by name, unambiguous abbreviation,
registry institution or city; the query that found it is never evidence; (3) a public actor is involved (government,
court, police, mission, university, research institute, or the state itself), with documented exceptions for
opportunities and state-level AI infrastructure investment; (4) an activity rule fires. Rejected items are kept with a
reason in `excluded_records.csv`.

## State attribution
State names are normalised (aliases such as Orissa/Keralam; abbreviations only in unambiguous forms like "MP govt";
the "New Delhi" dateline is not Delhi). One state per record; others mentioned are noted in "Why this state".

## Classification and stage
Six categories by transparent keyword rules (headline first, description as fallback), with a confidence level. The
**stage** label (proposed / announced / implemented / unclear) reads the headline's verbs only. It helps separate plans
from announcements from things reported as running; it is not a maturity assessment.

## Evidence status and links
| Status | Meaning |
|---|---|
| Primary source | Published by a government or academic body |
| Corroborated | Reported by two or more publishers |
| Single secondary source | One established outlet or think tank |
| Unverified | Unrecognised publisher, no corroboration |

This describes support in the sources held. **It is not a fact-check, and no record has been manually verified.** A
working link shows where a claim was reported; it does not verify it. *Direct publisher links* point to the article;
*Google News redirects* open it via news.google.com (the original URL is not provided by the feed).

## Deduplication
Exact repeats of the same URL collapse first and never count as corroboration. Reports of the same announcement by
different outlets are merged by fuzzy headline matching within a state and a 21-day window (named opportunities also by
programme name). The merge is conservative: some reworded duplicates remain separate. Every merge is in `duplicates.csv`
and visible in each record's detail view.

## Dates and summaries
Dates are **source publication dates**; the date an activity happened is not determined. Records without a publisher
description are labelled headline-only; headlines are never presented as summaries.

## Known biases and limitations
- English-language sources only; regional-language reporting and state portals are largely missing. States with more
  English coverage appear more active.
- Record counts measure **reporting volume**, not activity, capability or maturity, and are not a ranking.
- "No records found" means none were found in this collection, not that no activity exists.
- Classification is rule-based and has not been evaluated against a labelled set; manual audits found more noise among
  API-only records than RSS records.
- No state scores or benchmarks are produced.

Full detail: `docs/methodology.md` and `docs/limitations.md` in the repository.
""")
    with right:
        st.markdown("<h2>This collection</h2>", unsafe_allow_html=True)
        reasons = SUMMARY.get("exclusion_reasons", {})
        funnel = [("Raw items collected", SUMMARY.get("raw_entries", 0)),
                  ("Exact URL repeats collapsed", reasons.get("exact_url_repeat", 0)),
                  ("Rejected by inclusion rules or validation",
                   SUMMARY.get("excluded", 0) - reasons.get("exact_url_repeat", 0)),
                  ("Records after merging duplicate reports", SUMMARY.get("after_dedup_records", 0)),
                  ("Published activities", SUMMARY.get("published_activities", 0)),
                  ("Published opportunities", SUMMARY.get("published_opportunities", 0))]
        st.markdown("<table class='tbl'>" + "".join(f"<tr><td>{esc(k)}</td><td class='n'>{v:,}</td></tr>"
                                                    for k, v in funnel) + "</table>", unsafe_allow_html=True)
        st.markdown(f'<div class="muted" style="margin-top:0.4rem">Collected {esc(COLLECTED)}.</div>',
                    unsafe_allow_html=True)
        with st.expander("Why items were rejected"):
            rr = pd.DataFrame(sorted(reasons.items(), key=lambda kv: -kv[1]), columns=["Reason", "Items"])
            st.dataframe(rr, hide_index=True, use_container_width=True)
        with st.expander("Contribution by discovery channel"):
            ch = SUMMARY.get("by_discovery_source", {})
            if ch:
                st.dataframe(pd.DataFrame([{"Channel": DISCOVERY_LABELS.get(k, k), "Raw items": v["raw_items"],
                                            "Records contributed to": v["published_records_contributed_to"],
                                            "Found only by this channel": v["published_records_found_only_by_this_source"]}
                                           for k, v in ch.items()]), hide_index=True, use_container_width=True)
        st.markdown("<h2>Downloads</h2>", unsafe_allow_html=True)
        for label, name, mime in [("Activities (CSV)", "activities.csv", "text/csv"),
                                  ("Opportunities (CSV)", "opportunities.csv", "text/csv"),
                                  ("Full workbook (XLSX)", "ai_policy_activity.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                                  ("Excluded items with reasons (CSV)", "excluded_records.csv", "text/csv"),
                                  ("Duplicate merges (CSV)", "duplicates.csv", "text/csv"),
                                  ("Source registry (CSV)", "source_registry.csv", "text/csv"),
                                  ("State research coverage (CSV)", "state_coverage.csv", "text/csv")]:
            b = file_bytes(name)
            if b:
                st.download_button(label, b, name, mime, use_container_width=True, key=f"dl_{name}")
    st.markdown("<h2>Source registry</h2>", unsafe_allow_html=True)
    st.markdown('<div class="muted">Every publisher observed, how it was classified and why, plus reviewed official seed '
                'sites with their last reachability check.</div>', unsafe_allow_html=True)
    if not REG.empty:
        reg = REG.assign(source_type=REG["source_type"].map(SOURCE_TYPE_LABELS).fillna(REG["source_type"]))
        st.dataframe(reg[["source_name", "domain", "source_type", "records_in_dataset", "classification_reason", "origin"]]
                     .rename(columns={"source_name": "Source", "domain": "Domain", "source_type": "Type",
                                      "records_in_dataset": "Records", "classification_reason": "Why classified so",
                                      "origin": "Origin"}), hide_index=True, use_container_width=True, height=360)
    st.markdown("<h2>Research coverage by state / UT</h2>", unsafe_allow_html=True)
    if not COV.empty:
        cv = COV.assign(evidence_status=COV["evidence_status"].map(EVIDENCE_LABELS).fillna(COV["evidence_status"]))
        st.dataframe(cv[["state", "state_type", "raw_items_retrieved_for_state_queries", "records", "distinct_publishers",
                         "primary_source_records", "corroborated_records", "categories_covered", "evidence_status"]]
                     .rename(columns={"state": "State / UT", "state_type": "Type",
                                      "raw_items_retrieved_for_state_queries": "Items screened", "records": "Records",
                                      "distinct_publishers": "Publishers", "primary_source_records": "Primary",
                                      "corroborated_records": "Corroborated", "categories_covered": "Categories",
                                      "evidence_status": "Evidence (this collection)"}),
                     hide_index=True, use_container_width=True, height=360)


# ------------------------------------------------------------------ route
{"Overview": overview, "State Intelligence": state_intelligence, "Activity Explorer": activity_explorer,
 "Opportunities": opportunities, "Methodology": methodology}[section]()

# keep the address bar shareable: section and state
st.query_params.update({"section": section, **({"state": ss.focus_state} if ss.focus_state in REGION_NAMES else {})})
if ss.focus_state not in REGION_NAMES and "state" in st.query_params:
    del st.query_params["state"]
