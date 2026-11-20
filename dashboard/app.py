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
from dashboard.data import (ACTIVITY_STAGE_LABELS, ACTOR_CLASS_LABELS, CATEGORY_LABELS, CATEGORY_ORDER,  # noqa: E402
                            DISCOVERY_LABELS, EVIDENCE_LABELS, LEVEL_LABELS, REGION_GROUPS, REGION_KIND, REGION_NAMES,
                            REVIEW_LABELS, SCOPE_LABELS, SECTOR_LABELS, SOURCE_TYPE_LABELS,
                            STAGE_LABELS, STAGE_ORDER, URL_TYPE_LABELS, VERIFICATION_LABELS, VERIFICATION_ORDER,
                            file_bytes, load_all, search_mask)
from dashboard.ui import (BLUE, CSS, INK2, MAP_METRICS, RULE, brief_item_html, build_map, category_table_html, esc,  # noqa: E402
                          hbar, hotspots, record_browser, record_row_html, render_detail, select_callback,
                          deadline_display, selected_points, state_metrics, stats_html)
from functools import partial  # noqa: E402

st.set_page_config(page_title="India AI Policy & Ecosystem Intelligence", page_icon="🗺️", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)

SECTIONS = ["Overview", "State Intelligence", "Activity Explorer", "Opportunities", "Stakeholders", "Methodology"]
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
NAT, STAKE = D["national"], D["stakeholders"]
ALL = pd.concat([ACTS, NAT], ignore_index=True) if not NAT.empty else ACTS
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


EXPLORER_KEYS = ("ax_q", "ax_states", "ax_cats", "ax_secs", "ax_ev", "ax_stage", "ax_link", "ax_dates", "ax_actor",
                 "ax_scope", "ax_astage")


def explorer_defaults() -> dict:
    """Explicit empty values for every Explorer widget. Widgets must be SET to these (not popped):
    a popped key leaves the old value in the browser, which is re-sent on the next interaction."""
    d0, d1 = ALL["published"].min().date(), ALL["published"].max().date()
    return {k: ("" if k == "ax_q" else (d0, d1) if k == "ax_dates" else []) for k in EXPLORER_KEYS}


def drill_seq() -> int:
    return ss.get("drill_seq", 0)


def drill_to_explorer(label: str, origin: str, **filters) -> None:
    """Open Activity Explorer with explicit filters. The previous Explorer state and the
    originating section are remembered so 'Back to chart' restores them exactly."""
    ss.drill = {"label": label, "origin": origin, "restore": {k: ss[k] for k in EXPLORER_KEYS if k in ss}}
    for k, v in explorer_defaults().items():
        ss[k] = v
    for k, v in filters.items():
        ss[k] = v
    ss.drill_seq = drill_seq() + 1          # fresh chart keys: the same bar can be clicked again later
    ss.nav = "Activity Explorer"


def drill_back() -> None:
    d = ss.pop("drill", None) or {}
    for k, v in explorer_defaults().items():
        ss[k] = v
    for k, v in d.get("restore", {}).items():
        ss[k] = v
    ss.nav = d.get("origin", "Activity Explorer")


def chart_click(key: str, make: callable) -> None:
    """on_select callback: turn the clicked point's customdata into a drill-down."""
    pts = selected_points(key)
    if pts:
        cd = pts[0].get("customdata")
        if cd is not None:
            make(cd if not isinstance(cd, list) or len(cd) > 1 else cd[0])


def clickable(fig, key: str, make: callable) -> None:
    k = f"{key}_{drill_seq()}"
    st.plotly_chart(fig, use_container_width=True, key=k, on_select=partial(chart_click, k, make),
                    selection_mode="points", config={"displayModeBar": False})


# ------------------------------------------------------------------ header + navigation
h1, h2 = st.columns([0.8, 1.6], vertical_alignment="bottom")
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
        counts = ALL["category"].value_counts().reindex(CATEGORY_ORDER).fillna(0).astype(int)
        clickable(hbar([CATEGORY_LABELS[c] for c in counts.index], counts.tolist(), 300, "records", len(ALL),
                       keys=list(counts.index)), "ov_cat",
                  lambda c: drill_to_explorer(f"Overview · category chart: {CATEGORY_LABELS[c]} (all India)", "Overview",
                                              ax_cats=[c]))
        st.markdown(f'<div class="muted">Records per category across India ({len(ALL)} incl. national-scope; share of '
                    'all). <b>Click a bar</b> to list those records.</div>', unsafe_allow_html=True)
    with b:
        st.markdown("<h3>Who acted</h3>", unsafe_allow_html=True)
        cls = ALL["actor_classes"].str.split("|").explode()
        cls = cls[cls != ""].map(ACTOR_CLASS_LABELS).value_counts()
        label_to_key = {v: k for k, v in ACTOR_CLASS_LABELS.items()}
        top = cls.head(8)
        clickable(hbar(top.index.tolist(), top.values.tolist(), 300, "records",
                       keys=[label_to_key[x] for x in top.index]), "ov_actor",
                  lambda k: drill_to_explorer(f"Overview · who acted: {ACTOR_CLASS_LABELS[k]}", "Overview", ax_actor=[k]))
        n_none = int((ALL["actors"] == "").sum())
        st.markdown(f'<div class="muted">Actor types named in headlines (a record can name several). {n_none} of '
                    f'{len(ALL)} records name no identifiable actor in the headline. Identity only; legal authority '
                    'is stated only for registry bodies. <b>Click a bar</b> to list those records.</div>', unsafe_allow_html=True)
    intelligence_brief()


def intelligence_brief() -> None:
    st.markdown("<h2>India AI Intelligence Brief</h2>", unsafe_allow_html=True)
    windows = {"30 days": 30, "90 days": 90, "6 months": 182, "12 months": 366}
    c1, c2 = st.columns([1.2, 2], vertical_alignment="center")
    w = c1.segmented_control("Sources published in the last", list(windows), default="90 days", key="brief_window") or "90 days"
    asof = pd.Timestamp(COLLECTED) if COLLECTED != "unknown" else ALL["published"].max()
    since = asof - pd.Timedelta(days=windows[w])
    c2.markdown(f'<div class="muted">Records whose <b>source was published</b> between {since:%d %b %Y} and '
                f'{asof:%d %b %Y} (collection date). Publication date is not the activity date. Within each region, items '
                'are ordered by strength of sourcing (official source or 2+ publishers first), then whether an actor is '
                'identified, number of reports and recency. Items are records, not assessments; no significance is '
                'added beyond what the source states.</div>', unsafe_allow_html=True)
    W = ALL[ALL["published"].between(since, asof)]
    W = W.assign(_has_actor=W["actors"] != "").sort_values(
        ["strong_evidence", "_has_actor", "duplicate_count", "published"], ascending=False)

    def block(title: str, sub: pd.DataFrame, note: str, states: list[str] | None, key: str) -> None:
        st.markdown(f"<h3 style='margin-top:0.8rem'>{esc(title)}</h3><div class='muted'>{esc(note)} · "
                    f"{len(sub)} record{'s' if len(sub) != 1 else ''} in window</div>", unsafe_allow_html=True)
        if sub.empty:
            st.markdown('<div class="note">No qualifying records in this window. This reflects the collection, not '
                        'an absence of activity.</div>', unsafe_allow_html=True)
            return
        st.markdown("".join(brief_item_html(i, r) for i, (_, r) in enumerate(sub.head(5).iterrows(), 1)),
                    unsafe_allow_html=True)
        if len(sub) > 5:
            st.button(f"All {len(sub)} in Activity Explorer →", key=f"brief_more_{key}", on_click=open_in_explorer,
                      args=(states, since.date(), asof.date()))

    block("India: national developments", W[W["geographic_scope"] == "national"],
          "Union ministries, regulators, Parliament, Supreme Court, national missions; no state named", ["India (national)"], "nat")
    cols = st.columns(2, gap="large")
    for i, (region, sts) in enumerate(REGION_GROUPS.items()):
        with cols[i % 2]:
            block(region, W[W["state"].isin(sts)], ", ".join(sts), sts, region)
    with st.expander("How regions are defined"):
        st.markdown("Adapted from the Zonal Councils (States Reorganisation Act, 1956). Central Zonal Council members are "
                    "assigned to the nearest of the five groups (Uttar Pradesh, Uttarakhand, Madhya Pradesh to Northern; "
                    "Chhattisgarh to Eastern); Andaman & Nicobar and Lakshadweep to Southern. Multi-state records appear "
                    "under the region of their primary state.")


def open_in_explorer(states: list[str] | None, d0, d1) -> None:
    drill_to_explorer(f"Intelligence brief: {', '.join(states or [])[:80]}", "Overview", ax_states=states or [],
                      ax_dates=(max(d0, ALL["published"].min().date()), min(d1, ALL["published"].max().date())))


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
    counts = sub["category"].value_counts().reindex(CATEGORY_ORDER).fillna(0).astype(int)
    clickable(hbar([CATEGORY_LABELS[c] for c in counts.index], counts.tolist(), 240, "records", keys=list(counts.index)),
              f"ov_state_cat_{name}",
              lambda c, n=name: drill_to_explorer(f"Overview · {n} profile: {CATEGORY_LABELS[c]}", "Overview",
                                                  ax_states=[n], ax_cats=[c]))
    st.markdown('<div class="muted">Click a bar to list that state\'s records in the category. 0 = none found in '
                'this collection.</div>', unsafe_allow_html=True)
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

    cls = sub["actor_classes"].str.split("|").explode()
    cls = cls[cls != ""].map(ACTOR_CLASS_LABELS).value_counts()
    stg = sub["activity_stage"].value_counts()
    st.markdown('<div class="muted"><b>Who acted</b> (actor types named in headlines): '
                + (esc(", ".join(f"{k} {v}" for k, v in cls.items())) if not cls.empty else "none identified")
                + f' · {int((sub["actors"] == "").sum())} records name no identifiable actor.<br><b>Evidence-backed stage</b> '
                + esc(", ".join(f"{ACTIVITY_STAGE_LABELS[k]} {v}" for k, v in stg.items() if k != "undetermined") or "none")
                + f' · undetermined {int(stg.get("undetermined", 0))} (stage is assigned only when an official source or '
                '2+ publishers report the step).</div>', unsafe_allow_html=True)
    st.markdown("<h2>Activity by area</h2>", unsafe_allow_html=True)
    st.markdown('<div class="muted">Stage columns read the headline\'s wording (e.g. "plans to", "approves", '
                '"rolls out"). They separate proposals from announcements from things reported as running; they are not '
                'an assessment of progress on the ground.</div>', unsafe_allow_html=True)
    counts = sub["category"].value_counts().reindex(CATEGORY_ORDER).fillna(0).astype(int)
    clickable(hbar([CATEGORY_LABELS[c] for c in counts.index], counts.tolist(), 250, "records", keys=list(counts.index)),
              f"si_cat_chart_{name}",
              lambda c, n=name: drill_to_explorer(f"State Intelligence · {n}: {CATEGORY_LABELS[c]}", "State Intelligence",
                                                  ax_states=[n], ax_cats=[c]))
    st.markdown('<div class="muted"><b>Click a bar</b> to open those records in Activity Explorer. The table adds the '
                'headline-wording stage split.</div>', unsafe_allow_html=True)
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
TREND_COLORS = dict(zip(CATEGORY_ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]))  # validated set


def reset_explorer() -> None:
    for k, v in explorer_defaults().items():
        ss[k] = v
    ss.pop("drill", None)
    ss.drill_seq = drill_seq() + 1


def explorer_filtered(q: str) -> pd.DataFrame:
    R = ALL[search_mask(ALL, q)]
    for col, key in (("state", "ax_states"), ("category", "ax_cats"), ("sector", "ax_secs"),
                     ("verification_status", "ax_ev"), ("stage_cue", "ax_stage"), ("url_type", "ax_link"),
                     ("geographic_scope", "ax_scope"), ("activity_stage", "ax_astage")):
        if ss.get(key):
            R = R[R[col].isin(ss[key])]
    if ss.get("ax_actor"):
        want = set(ss["ax_actor"])
        R = R[R["actor_classes"].map(lambda s: bool(want & set(s.split("|"))) or ("unknown" in want and not s))]
    dmin, dmax = ALL["published"].min().date(), ALL["published"].max().date()
    d = ss.get("ax_dates", (dmin, dmax))
    if tuple(d) != (dmin, dmax):
        R = R[R["published"].between(pd.Timestamp(d[0]), pd.Timestamp(d[1]))]
    return R


def active_filter_chips(dmin, dmax) -> list[str]:
    fmt = {"ax_states": ("State / UT", str), "ax_cats": ("Category", CATEGORY_LABELS.get),
           "ax_secs": ("Sector", SECTOR_LABELS.get), "ax_ev": ("Evidence", VERIFICATION_LABELS.get),
           "ax_stage": ("Headline wording", STAGE_LABELS.get), "ax_link": ("Link", URL_TYPE_LABELS.get),
           "ax_actor": ("Actor type", lambda k: ACTOR_CLASS_LABELS.get(k, "No actor identified")),
           "ax_scope": ("Scope", SCOPE_LABELS.get), "ax_astage": ("Activity stage", ACTIVITY_STAGE_LABELS.get)}
    chips = []
    if ss.get("ax_q"):
        chips.append(f'Search: “{ss["ax_q"]}”')
    for k, (lab, f) in fmt.items():
        if ss.get(k):
            chips.append(f"{lab}: " + ", ".join(str(f(v)) for v in ss[k]))
    d = ss.get("ax_dates", (dmin, dmax))
    if tuple(d) != (dmin, dmax):
        chips.append(f"Published: {d[0]:%d %b %Y} – {d[1]:%d %b %Y}")
    return chips


def activity_explorer() -> None:
    dmin, dmax = ALL["published"].min().date(), ALL["published"].max().date()
    if "ax_dates" not in ss:
        ss.ax_dates = (dmin, dmax)
    drill = ss.get("drill")
    if drill:
        b1, b2, b3 = st.columns([3, 1, 1], vertical_alignment="center")
        b1.markdown(f'<div class="note" style="margin:0"><b>Opened from a chart:</b> {esc(drill["label"])}</div>',
                    unsafe_allow_html=True)
        b2.button(f"← Back to {drill['origin']}", on_click=drill_back, use_container_width=True)
        b3.button("Clear and show all", on_click=reset_explorer, use_container_width=True, key="drill_clear")

    q = st.text_input("Search all of India", key="ax_q",
                      placeholder='Search every state, UT and national record, e.g.  collab   ·   "AI safety"   ·   IIT Madras',
                      help="All words must match (AND); case-insensitive; partial words match ('collab' finds "
                           "'collaboration'). \"Quoted phrases\" match exactly. No state needs to be selected.")
    st.markdown('<div class="muted">Searches headline, publisher description, actors and actor types, institutions, '
                'publisher, state, city, region, category, sector, stage and evidence text across all state-level and '
                'national records. State selection below only narrows results.</div>', unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns([1.3, 1.3, 1, 1.4], vertical_alignment="bottom")
    f1.multiselect("States / UTs (optional)", REGION_NAMES + ["India (national)"], key="ax_states",
                   placeholder="All of India")
    f2.multiselect("Category", CATEGORY_ORDER, format_func=CATEGORY_LABELS.get, key="ax_cats", placeholder="All")
    f3.multiselect("Evidence", VERIFICATION_ORDER, format_func=VERIFICATION_LABELS.get, key="ax_ev", placeholder="All",
                   help="Support in the sources held. Not a fact-check.")
    f4.slider("Source published", min_value=dmin, max_value=dmax, format="MMM YYYY", key="ax_dates",
              help="Publication date of the source, not the date the activity happened.")
    with st.expander("Advanced filters"):
        a1, a2, a3 = st.columns(3)
        a1.multiselect("Sector", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get, key="ax_secs", placeholder="All")
        a2.multiselect("Actor type", [k for k in ACTOR_CLASS_LABELS if k != "unknown"] + ["unknown"],
                       format_func=lambda k: ACTOR_CLASS_LABELS[k] if k != "unknown" else "No actor identified",
                       key="ax_actor", placeholder="All", help="Identity of actors named in the headline.")
        a3.multiselect("Geographic scope", list(SCOPE_LABELS)[:3], format_func=SCOPE_LABELS.get, key="ax_scope",
                       placeholder="All")
        a4, a5, a6 = st.columns(3)
        a4.multiselect("Activity stage (evidence-based)", list(ACTIVITY_STAGE_LABELS), format_func=ACTIVITY_STAGE_LABELS.get,
                       key="ax_astage", placeholder="All",
                       help="Assigned only when an official source or 2+ publishers report the step.")
        a5.multiselect("Headline wording", STAGE_ORDER, format_func=STAGE_LABELS.get, key="ax_stage", placeholder="All")
        a6.multiselect("Link type", list(URL_TYPE_LABELS), format_func=URL_TYPE_LABELS.get, key="ax_link", placeholder="All")

    chips = active_filter_chips(dmin, dmax)
    c1, c2 = st.columns([5, 1], vertical_alignment="center")
    c1.markdown('<div style="margin:0.2rem 0">' + ("".join(f'<span class="tag strong">{esc(c)}</span>' for c in chips)
                if chips else '<span class="muted">No filters: showing the full dataset.</span>') + "</div>",
                unsafe_allow_html=True)
    if chips:
        c2.button("Clear all filters", on_click=reset_explorer, use_container_width=True, key="clear_all")

    R = explorer_filtered(q)
    n_states = R.loc[R["state"].isin(REGION_NAMES), "state"].nunique()
    n_nat = int((R["geographic_scope"] == "national").sum())
    st.markdown(stats_html([(f"{len(R):,}", f"matching records across India (of {len(ALL):,})"),
                            (f"{n_states} of 36", "states / UTs represented"),
                            (str(n_nat), "national-level records (no state attribution)"),
                            (str(int(R["strong_evidence"].sum())), "well-sourced (primary or 2+ publishers)")]),
                unsafe_allow_html=True)
    if R.empty:
        st.markdown('<div class="note"><b>No records match.</b> Try fewer words, a partial word (e.g. "collab"), or '
                    'removing a filter. Zero matches means nothing in this collection matched, <b>not</b> that no AI '
                    'activity exists in the selected states.</div>', unsafe_allow_html=True)
        return

    m1, m2 = st.columns([1.25, 1], gap="large")
    with m1:
        mk = f"ax_map_{drill_seq()}"
        fig = build_map("records", state_metrics(R), None, GEO, None, height=520)
        st.plotly_chart(fig, use_container_width=True, key=mk, on_select=select_callback(mk), selection_mode="points",
                        config={"displayModeBar": False, "scrollZoom": False})
        if ss.get(mk) and selected_points(mk) and ss.focus_state in REGION_NAMES:
            st.button(f"Open {ss.focus_state} profile →", on_click=go_to, args=("State Intelligence",), type="primary")
        st.markdown(f'<div class="muted">Where the {len(R):,} matching records are attributed. {n_nat} national-level '
                    'records have no state and are not mapped. Clicking a state selects it for its profile; it does '
                    '<b>not</b> change your search or filters.</div>', unsafe_allow_html=True)
    with m2:
        st.markdown("<h3>Matches by state / UT</h3>", unsafe_allow_html=True)
        by = R["state"].value_counts()
        st.markdown("<table class='tbl'>" + "".join(f"<tr><td>{esc(k)}</td><td class='n'>{v}</td></tr>"
                                                     for k, v in by.head(14).items()) + "</table>", unsafe_allow_html=True)
        if len(by) > 14:
            st.markdown(f'<div class="muted">+ {len(by) - 14} more.</div>', unsafe_allow_html=True)

    st.markdown("<h3>Records</h3>", unsafe_allow_html=True)
    record_browser(R, DUPS, key=f"ax_table_{drill_seq()}")
    st.download_button("Download these records (CSV)",
                       R.drop(columns=["published", "deadline_dt", "app_deadline_dt", "link", "search_text"], errors="ignore")
                       .to_csv(index=False).encode(), "ai_policy_records_filtered.csv", "text/csv")

    st.markdown("<h3>Reporting volume over time (matching records)</h3>", unsafe_allow_html=True)
    T = R[R["published"].notna()]
    T = T.assign(month=T["published"].dt.to_period("M").dt.to_timestamp())
    piv = T.pivot_table(index="month", columns="category", values="record_id", aggfunc="count", fill_value=0)
    fig = go.Figure()
    for c in CATEGORY_ORDER:
        if c in piv:
            fig.add_trace(go.Bar(x=piv.index, y=piv[c], name=CATEGORY_LABELS[c], marker_color=TREND_COLORS[c],
                                 marker_line=dict(color="#ffffff", width=1.5),
                                 customdata=[[d.strftime("%Y-%m"), c] for d in piv.index],
                                 selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)),
                                 hovertemplate="%{x|%b %Y} · " + CATEGORY_LABELS[c] + ": %{y}<br><i>click to list</i><extra></extra>"))
    fig.update_layout(barmode="stack", height=360, margin=dict(l=0, r=0, t=6, b=0), bargap=0.25, clickmode="event+select",
                      dragmode=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=-0.18, font=dict(size=11, color=INK2), traceorder="normal"),
                      xaxis=dict(tickformat="%b %Y", tickfont=dict(color=INK2), showgrid=False),
                      yaxis=dict(title=dict(text="Records by source publication month", font=dict(size=11, color=INK2)),
                                 gridcolor=RULE, zeroline=False))

    def month_drill(cd):
        month, cat = cd
        p = pd.Period(month, "M")
        d0 = max(p.start_time.date(), dmin); d1 = min(p.end_time.date(), dmax)
        keep = {k: ss[k] for k in EXPLORER_KEYS if k in ss and k not in ("ax_cats", "ax_dates")}
        drill_to_explorer(f"Trend chart: {CATEGORY_LABELS[cat]}, {p.strftime('%B %Y')}", "Activity Explorer",
                          **keep, ax_cats=[cat], ax_dates=(d0, d1))

    clickable(fig, "ax_trend", month_drill)
    st.markdown('<div class="muted"><b>Click a segment</b> to list that month and category (other filters are kept; '
                '"Back" restores the previous view). Months are source publication months, not activity dates; news APIs '
                'reach back only ~30 days, so the latest month is partly API-driven.</div>', unsafe_allow_html=True)


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
        when, evidence = deadline_display(r, asof)
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
            + (f'<div class="m">Evidence: “{esc(evidence)}”</div>' if evidence else "")
            + f'<div class="m">Review note: {esc(r["review_note"] or "—")}</div></div>', unsafe_allow_html=True)
        details = [(lab, r[c]) for lab, c in (("Programme / event dates", "programme_dates"), ("Eligibility", "eligibility"),
                                               ("Fees / stipend", "fees_stipend"), ("Mode / location", "location_mode"),
                                               ("Application URL", "application_url"), ("Organiser", "organiser")) if r[c]]
        if details or r["deadline_source_url"]:
            with st.expander("Details extracted from the source (evidence excerpts)"):
                for lab, v in details:
                    st.markdown(f'<div class="kv"><div class="k">{esc(lab)}</div><div class="v">'
                                f'{esc(v.replace(" || ", " … "))}</div></div>', unsafe_allow_html=True)
                if r["deadline_source_url"]:
                    st.markdown(f'<div class="muted">Deadline source: {esc(r["deadline_source_url"])} · checked '
                                f'{esc(r["enrichment_checked_on"])}</div>', unsafe_allow_html=True)


# ================================================================== STAKEHOLDERS
def stakeholders() -> None:
    st.markdown('<p class="lede">Organisations from the project registry that appear as actors in at least one record: '
                'government bodies, regulators, courts, missions, universities and research institutes, AI labs and '
                'technology companies, think tanks and international organisations.</p>', unsafe_allow_html=True)
    st.markdown('<div class="note">A public <b>institutional</b> directory, not a contact list. No individuals are listed. '
                'Identity and, for statutory bodies, the stated legal basis come from a curated registry; focus areas are '
                'the categories of linked records, not an assessment of expertise. Official websites are curated and their '
                'reachability is checked on the date shown; contact routes beyond the official website have not been '
                'collected. Companies and labs are listed where Indian activity was reported.</div>', unsafe_allow_html=True)
    if STAKE.empty:
        st.info("No stakeholder data. Run the pipeline.")
        return
    S_ = STAKE.copy()
    S_["Type"] = S_["entity_class"].map(ACTOR_CLASS_LABELS).fillna(S_["entity_class"])
    S_["Level"] = S_["level"].map(LEVEL_LABELS).fillna(S_["level"])
    S_["linked_records"] = pd.to_numeric(S_["linked_records"], errors="coerce").fillna(0).astype(int)
    types = sorted(S_["Type"].unique())
    pick = st.multiselect("Type", types, key="sk_type", placeholder="All types")
    V = S_[S_["Type"].isin(pick)] if pick else S_
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        ev = st.dataframe(V[["entity", "Type", "Level", "linked_records", "latest_record_date"]]
                          .rename(columns={"entity": "Organisation", "linked_records": "Records",
                                           "latest_record_date": "Latest source"}),
                          hide_index=True, use_container_width=True, height=520, on_select="rerun",
                          selection_mode="single-row", key="sk_table")
    with right:
        if not ev.selection.rows:
            st.markdown('<div class="note">Select an organisation to see its profile and the records that name it.</div>',
                        unsafe_allow_html=True)
            return
        r = V.iloc[ev.selection.rows[0]]
        st.markdown(f'<div class="eyebrow">{esc(r["Type"])} · {esc(r["Level"])}</div><h2 style="margin-top:0.1rem !important">'
                    f'{esc(r["entity"])}</h2>', unsafe_allow_html=True)
        rows = [("Location", r["location"] or "Not established"),
                ("Authority / basis", r["authority_note"] or "Not stated (not in curated registry)"),
                ("Linked records", f'{r["linked_records"]} (states: {r["linked_states"].replace("|", ", ")})'),
                ("Focus areas (from records)", r["focus_areas_from_records"].replace("|", "; ")),
                ("Official website", r["official_website"] or "None curated"),
                ("Website check", r["website_check"]),
                ("Public contact route", r["public_contact_route"]),
                ("Entry basis", r["entry_basis"])]
        st.markdown('<div class="kv">' + "".join(f'<div class="k">{esc(k)}</div><div class="v">{esc(v)}</div>'
                                                 for k, v in rows) + "</div>", unsafe_allow_html=True)
        if r["official_website"]:
            st.link_button("Official website ↗", r["official_website"])
        ids = [x for x in r["evidence_record_ids"].split("|") if x]
        linked = pd.concat([ALL, OPPS], ignore_index=True)
        linked = linked[linked["record_id"].isin(ids)].sort_values("published", ascending=False)
        st.markdown("<h3 style='margin-top:0.8rem'>Records naming this organisation</h3>", unsafe_allow_html=True)
        st.markdown("".join(record_row_html(x) for _, x in linked.iterrows()), unsafe_allow_html=True)


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

## Actors, geography and stage
Each record lists the **actors named in its headline** (identity: ministry, regulator, court, state government,
university, AI lab…). Legal or administrative authority is stated only for bodies in the curated registry; otherwise it is
not asserted, and "no actor identified" is shown rather than guessed. **Geography** is split into the state attributed,
the basis for it (named in the headline, an institution's own location, a city), all states named, and scope
(state, multi-state, national). National activities by Union bodies are a separate dataset and are **not** assigned to
Delhi. **Activity stage** (proposed/announced, approved/constituted, operational…) is assigned only when an official
source or two or more publishers report the step; everything else is "undetermined". Discussion, ongoing
implementation and completion are not inferred from headlines.

## Classification and headline wording
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
                                  ("National-scope activities (CSV)", "national_activities.csv", "text/csv"),
                                  ("Stakeholder directory (CSV)", "stakeholders.csv", "text/csv"),
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
 "Opportunities": opportunities, "Stakeholders": stakeholders, "Methodology": methodology}[section]()

# keep the address bar shareable: section and state
st.query_params.update({"section": section, **({"state": ss.focus_state} if ss.focus_state in REGION_NAMES else {})})
if ss.focus_state not in REGION_NAMES and "state" in st.query_params:
    del st.query_params["state"]
