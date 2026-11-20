"""India AI Policy Tracker - Streamlit dashboard.

    streamlit run dashboard/app.py

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
from dashboard.data import (CATEGORY_COLORS, CATEGORY_LABELS, CATEGORY_ORDER, DISCOVERY_LABELS,  # noqa: E402
                            EVIDENCE_LABELS, REGION_KIND, REGION_NAMES, REGION_POINT, SECTOR_LABELS,
                            URL_TYPE_LABELS, VERIFICATION_LABELS, file_bytes, load_all)

st.set_page_config(page_title="India AI Policy Tracker", page_icon="🗺️", layout="wide")

INK, INK2, MUTED, SURFACE, GRID = "#0b0b0b", "#52514e", "#898781", "#fcfcfb", "#e8e7e3"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]   # one hue, light->dark
NO_EVIDENCE = "#e4e3df"
HOTSPOT = "#eb6834"

st.markdown(f"""
<style>
  .block-container {{padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1320px;}}
  h1 {{font-size: 1.85rem !important; font-weight: 650 !important; letter-spacing: -0.01em; margin-bottom: 0 !important;}}
  h3 {{font-size: 1.1rem !important; font-weight: 600 !important;}}
  .lede {{color: {INK2}; font-size: 0.98rem; margin: 0.2rem 0 0.9rem 0; max-width: 60rem;}}
  .note {{color: {INK2}; font-size: 0.84rem; border-left: 3px solid {GRID}; padding: 0.15rem 0 0.15rem 0.7rem; margin: 0.4rem 0 0.8rem 0;}}
  div[data-testid="stMetric"] {{background: {SURFACE}; border: 1px solid {GRID}; border-radius: 8px; padding: 0.7rem 0.9rem;}}
  div[data-testid="stMetricLabel"] p {{color: {INK2}; font-size: 0.82rem;}}
  div[data-testid="stMetricValue"] {{font-size: 1.6rem;}}
  .pill {{display:inline-block; font-size:0.75rem; padding:0.05rem 0.5rem; border-radius:999px; border:1px solid {GRID}; color:{INK2}; margin-right:0.3rem;}}
  .rec {{border-bottom: 1px solid {GRID}; padding: 0.55rem 0;}}
  .rec a {{color: {INK}; text-decoration: none; font-weight: 550;}}
  .rec a:hover {{text-decoration: underline;}}
  .meta {{color: {MUTED}; font-size: 0.8rem;}}
  section[data-testid="stSidebar"] {{border-right: 1px solid {GRID};}}
</style>""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def get_data(_stamp: float) -> dict:
    return load_all()


def data_stamp() -> float:
    p = Path(__file__).resolve().parent.parent / "data" / "processed" / "activities.csv"
    return p.stat().st_mtime if p.exists() else 0.0


D = get_data(data_stamp())
acts, opps, cov, reg, summary, geojson = (D["activities"], D["opportunities"], D["coverage"],
                                          D["registry"], D["summary"], D["geojson"])

if acts.empty:
    st.title("India AI Policy Tracker")
    st.warning("No processed data found. Run `python -m src.pipeline` first (see README).")
    st.stop()


# ----------------------------------------------------------------------------- filters
def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    if df.empty:
        return df
    m = pd.Series(True, index=df.index)
    if f["states"]:
        m &= df["state"].isin(f["states"])
    if f["categories"]:
        m &= df["category"].isin(f["categories"])
    if f["sectors"]:
        m &= df["sector"].isin(f["sectors"])
    if f["verification"]:
        m &= df["verification_status"].isin(f["verification"])
    if f["dates"]:
        lo, hi = (pd.Timestamp(x) for x in f["dates"])
        m &= df["published"].between(lo, hi) | df["published"].isna()
    if f["query"]:
        q = f["query"].casefold()
        hay = (df["title"] + " " + df["description_shown"] + " " + df["institutions"] + " " + df["source_name"]
               + " " + df["city"] + " " + df["state"]).str.casefold()
        m &= hay.str.contains(q, regex=False)
    return df[m]


with st.sidebar:
    st.markdown("### Filters")
    query = st.text_input("Search", placeholder="e.g. AI mission, IIT Madras, MoU", help="Searches headlines, publisher descriptions, institutions, sources, cities and states.")
    states = st.multiselect("States / UTs", REGION_NAMES, placeholder="All 36")
    categories = st.multiselect("Category", CATEGORY_ORDER, format_func=CATEGORY_LABELS.get, placeholder="All categories")
    sectors = st.multiselect("Sector", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get, placeholder="All sectors")
    verification = st.multiselect("Evidence status", list(VERIFICATION_LABELS), format_func=VERIFICATION_LABELS.get,
                                  placeholder="All", help="How well the record is supported by the sources held. Not a fact-check.")
    dmin, dmax = acts["published"].min(), acts["published"].max()
    dates = None
    if pd.notna(dmin) and pd.notna(dmax):
        dates = st.slider("Published between", min_value=dmin.date(), max_value=dmax.date(),
                          value=(dmin.date(), dmax.date()), format="MMM YYYY",
                          help="Publication date of the source, not the date the activity happened.")
        if dates == (dmin.date(), dmax.date()):
            dates = None
    st.caption(f"Data collected {summary.get('run_date', 'unknown')}. "
               "Records come from news discovery and are labelled by evidence strength.")

F = dict(query=query.strip(), states=states, categories=categories, sectors=sectors, verification=verification, dates=dates)
A = apply_filters(acts, F)
O = apply_filters(opps, {**F, "states": [s for s in states] + (["Pan-India"] if states else [])})

# ----------------------------------------------------------------------------- header
st.title("India AI Policy Tracker")
st.markdown('<p class="lede">Documented AI policy, governance, deployment, research, partnership and talent activity '
            'across Indian states and union territories, collected from public news and official feeds, deduplicated, '
            'and labelled with how strongly each record is sourced.</p>', unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Activity records", f"{len(A):,}", help="Distinct activities after merging duplicate reports across outlets.")
n_states = A.loc[A["state"].isin(REGION_NAMES), "state"].nunique()
k2.metric("States / UTs with records", f"{n_states} of 36")
strong = A["strong_evidence"].mean() * 100 if len(A) else 0
k3.metric("Primary or corroborated", f"{strong:.0f}%", help="Share of records published by an official source or reported by 2+ publishers.")
k4.metric("Opportunities", f"{len(O):,}", help="Fellowships, internships, workshops, hackathons and conferences.")

if len(A) and (A["strong_evidence"].mean() < 0.5):
    st.markdown(f'<div class="note">Most records rest on a single news report. Treat them as leads to check against the '
                f'linked source, not as confirmed facts. Record counts reflect English-language media coverage and are '
                f'not a ranking of states.</div>', unsafe_allow_html=True)

tab_map, tab_rec, tab_trend, tab_inst, tab_opp, tab_about = st.tabs(
    ["Map & state profiles", "Records", "Trends", "Institutions & sources", "Opportunities", "About the data"])


# ----------------------------------------------------------------------------- helpers
def record_html(r: pd.Series) -> str:
    title = r["title"] or "(untitled)"
    head = f'<a href="{r["link"]}" target="_blank" rel="noopener">{title}</a>' if r["link"] else title
    date = r["published"].strftime("%d %b %Y") if pd.notna(r["published"]) else "date unknown"
    desc = f'<div style="font-size:0.88rem;color:{INK2};margin-top:0.15rem">{r["description_shown"]}</div>' if r["description_shown"] else ""
    return (f'<div class="rec">{head}{desc}<div class="meta">{r["source_name"] or "unknown source"} · published {date} · '
            f'{r["state"]} · {r["category_label"]} · <b>{r["verification_label"]}</b> · {r["url_label"]}</div></div>')


def state_metrics(df: pd.DataFrame) -> pd.DataFrame:
    g = df[df["state"].isin(REGION_NAMES)].groupby("state")
    m = pd.DataFrame({"records": g.size(), "categories": g["category"].nunique(),
                      "strong": g["strong_evidence"].sum()}).reindex(REGION_NAMES).fillna(0).astype(int)
    return m.rename_axis("state").reset_index()


MAP_METRICS = {
    "records": ("Activities", "distinct activities found", "Documented activities"),
    "categories": ("Categories covered", "of 6 categories with ≥1 record", "Categories covered (of 6)"),
    "strong": ("Strong evidence", "primary-source or corroborated records", "Primary-source or corroborated records"),
}


def build_map(metric: str, m: pd.DataFrame, show_hotspots: bool, hot: pd.DataFrame) -> go.Figure:
    _, unit, label = MAP_METRICS[metric]
    has = m[m[metric] > 0]
    none = m[m[metric] == 0]
    fig = go.Figure()
    if geojson:
        fig.add_trace(go.Choropleth(
            geojson=geojson, featureidkey="properties.state", locations=none["state"], z=[0] * len(none),
            colorscale=[[0, NO_EVIDENCE], [1, NO_EVIDENCE]], showscale=False, marker_line_color="#ffffff",
            marker_line_width=0.6, customdata=none["state"], name="none",
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0.9)),
            hovertemplate="<b>%{customdata}</b><br>None found in this research<br>(not evidence of no activity)<extra></extra>"))
        fig.add_trace(go.Choropleth(
            geojson=geojson, featureidkey="properties.state", locations=has["state"], z=has[metric],
            colorscale=[[i / (len(SEQ) - 1), c] for i, c in enumerate(SEQ)], zmin=0,
            marker_line_color="#ffffff", marker_line_width=0.6, customdata=has["state"],
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0.9)),
            colorbar=dict(title=dict(text=label, side="right", font=dict(size=11, color=INK2)), thickness=10, len=0.6,
                          outlinewidth=0, tickfont=dict(size=10, color=INK2)),
            hovertemplate="<b>%{customdata}</b><br>%{z} " + unit + "<extra></extra>"))
    else:  # transparent fallback: approximate state points, no invented shapes
        pts = m.assign(lat=m["state"].map(lambda s: REGION_POINT[s][0]), lon=m["state"].map(lambda s: REGION_POINT[s][1]))
        fig.add_trace(go.Scattergeo(lat=pts["lat"], lon=pts["lon"], customdata=pts["state"], mode="markers",
                                    marker=dict(size=8 + pts[metric].clip(upper=60) ** 0.5 * 4, color=SEQ[4],
                                                line=dict(color="#ffffff", width=1.5)),
                                    hovertemplate="<b>%{customdata}</b><br>%{text}<extra></extra>",
                                    text=pts[metric].astype(str) + " " + unit))
    if show_hotspots and not hot.empty:
        fig.add_trace(go.Scattergeo(
            lat=hot["lat"], lon=hot["lon"], mode="markers", customdata=hot["state"], text=hot["place"],
            marker=dict(size=7 + hot["records"].clip(upper=40) ** 0.5 * 3, color=HOTSPOT, opacity=0.9,
                        line=dict(color="#ffffff", width=1.5)),
            hovertext=hot["records"].astype(str) + " record(s)",
            hovertemplate="<b>%{text}</b> · %{customdata}<br>%{hovertext}<extra></extra>",
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0.6)),
            name="Institution / city hotspots"))
    fig.update_geos(visible=False, fitbounds="locations", projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      clickmode="event+select", dragmode=False,
                      hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRID, font=dict(color=INK, size=12)))
    return fig


def on_map_select():
    sel = st.session_state.get("india_map")
    pts = (sel or {}).get("selection", {}).get("points", []) if sel else []
    for p in pts:
        name = p.get("customdata") or p.get("location")
        if isinstance(name, list):
            name = name[0]
        if name in REGION_NAMES:
            st.session_state["focus_state"] = name
            return


# ----------------------------------------------------------------------------- map tab
with tab_map:
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        c1, c2 = st.columns([2.2, 1], vertical_alignment="center")
        metric = c1.segmented_control("Shade states by", list(MAP_METRICS), format_func=lambda k: MAP_METRICS[k][0],
                                      default="records", label_visibility="collapsed") or "records"
        show_hot = c2.toggle("Hotspots", value=True,
                             help="Institution and city markers. Only records whose location is backed by the project's "
                                  "institution or city registry are placed; everything else is shown at state level.")
        located = A[A["lat"].notna() & A["lon"].notna()].copy()
        located["place"] = located["institutions"].str.split("|").str[0].where(located["institutions"] != "", located["city"])
        hot = (located.groupby(["place", "state", "lat", "lon"]).size().rename("records").reset_index()
               if not located.empty else pd.DataFrame())
        st.plotly_chart(build_map(metric, state_metrics(A), show_hot, hot), use_container_width=True,
                        key="india_map", on_select=on_map_select, selection_mode="points",
                        config={"displayModeBar": False, "scrollZoom": False})
        if geojson:
            st.caption("Click a state to open its profile. Grey = no records found in this research, which is not "
                       "evidence that nothing is happening there. Boundaries: community dataset (pinned, checksum-verified) "
                       "showing India's official external boundary; not an authoritative Survey of India product.")
        else:
            st.warning("State-boundary file missing or failed validation, so states are shown as approximate points "
                       "rather than drawing unverified shapes. Rebuild with `python scripts/build_boundaries.py`.")
    with right:
        options = ["—"] + REGION_NAMES
        if st.session_state.get("focus_state") not in options:
            st.session_state["focus_state"] = "—"
        focus = st.selectbox("State / UT profile", options, key="focus_state",
                             format_func=lambda s: "Select or click a state…" if s == "—" else s)
        if focus == "—":
            st.markdown("### Where the evidence is")
            sm = state_metrics(A).sort_values("records", ascending=False)
            sm = sm[sm["records"] > 0]
            st.markdown(f'<div class="note">States with the most documented activities in the current filter. '
                        f'This reflects reporting volume as much as activity.</div>', unsafe_allow_html=True)
            st.dataframe(sm.rename(columns={"state": "State / UT", "records": "Activities", "categories": "Categories",
                                            "strong": "Strong evidence"}),
                         hide_index=True, use_container_width=True, height=470)
        else:
            S_ = A[A["state"] == focus]
            crow = cov[cov["state"] == focus].iloc[0] if not cov.empty and (cov["state"] == focus).any() else None
            st.markdown(f"### {focus}")
            ev = EVIDENCE_LABELS.get(crow["evidence_status"], "—") if crow is not None else "—"
            st.markdown(f'<span class="pill">{REGION_KIND[focus]}</span><span class="pill">Overall: {ev}</span>',
                        unsafe_allow_html=True)
            a, b, c = st.columns(3)
            a.metric("Activities", len(S_))
            b.metric("Publishers", S_["source_name"].nunique())
            c.metric("Strong", int(S_["strong_evidence"].sum()), help="Primary-source or corroborated records.")
            if S_.empty:
                st.info("No records match the current filters for this state. Absence here reflects this research's "
                        "coverage, not necessarily an absence of activity.")
            else:
                counts = S_["category"].value_counts().reindex(CATEGORY_ORDER).fillna(0).astype(int)
                fig = go.Figure(go.Bar(
                    x=counts.values, y=[CATEGORY_LABELS[c] for c in counts.index], orientation="h",
                    marker=dict(color=[CATEGORY_COLORS[c] for c in counts.index], cornerradius=4),
                    text=counts.values, textposition="outside", textfont=dict(color=INK2, size=11), cliponaxis=False,
                    hovertemplate="%{y}: %{x}<extra></extra>"))
                fig.update_layout(height=230, margin=dict(l=0, r=30, t=8, b=0), plot_bgcolor="rgba(0,0,0,0)",
                                  paper_bgcolor="rgba(0,0,0,0)", bargap=0.35,
                                  xaxis=dict(visible=False, range=[0, max(counts.max(), 1) * 1.18]), yaxis=dict(autorange="reversed", tickfont=dict(size=11, color=INK2)))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                insts = sorted({i for s in S_["institutions"] for i in s.split("|") if i})
                if insts:
                    st.markdown("**Institutions named:** " + ", ".join(insts))
                span = S_["published"].dropna()
                if not span.empty:
                    st.caption(f"Sources published {span.min():%b %Y} – {span.max():%b %Y}.")
                st.markdown("**Latest records**")
                st.markdown("".join(record_html(r) for _, r in S_.sort_values("published", ascending=False).head(6).iterrows()),
                            unsafe_allow_html=True)


# ----------------------------------------------------------------------------- records tab
with tab_rec:
    focus = st.session_state.get("focus_state", "—")
    R = A
    c1, c2, c3 = st.columns(3)
    hide_unv = c1.checkbox("Hide unverified", value=False)
    direct_only = c2.checkbox("Direct publisher links only", value=False)
    if focus != "—":
        if c3.checkbox(f"Only {focus} (selected on map)", value=True):
            R = R[R["state"] == focus]
    if hide_unv:
        R = R[R["verification_status"] != "unverified"]
    if direct_only:
        R = R[R["url_type"] == "publisher_direct"]
    st.caption(f"{len(R):,} records. ‘Published’ is the source's publication date, not the date of the activity. "
               "A working link shows where a claim was reported; it does not verify the claim.")
    view = R.sort_values("published", ascending=False).assign(
        published_str=lambda d: d["published"].dt.strftime("%Y-%m-%d").fillna("unknown"),
        description=lambda d: d["description_shown"].where(d["description_shown"] != "", "— headline only —"))
    st.dataframe(
        view[["published_str", "state", "category_label", "title", "description", "source_name", "verification_label",
              "url_label", "link", "institutions", "sector_label", "discovery_label", "duplicate_count"]],
        hide_index=True, use_container_width=True, height=560,
        column_config={
            "published_str": st.column_config.TextColumn("Published", width="small"),
            "state": "State / UT", "category_label": "Category",
            "title": st.column_config.TextColumn("Headline", width="large"),
            "description": st.column_config.TextColumn("Publisher description", width="medium",
                                                       help="Description supplied by the publisher, where available. Headlines are not summaries."),
            "source_name": "Source", "verification_label": "Evidence status", "url_label": "Link type",
            "link": st.column_config.LinkColumn("Link", display_text="open ↗"),
            "institutions": "Institutions", "sector_label": "Sector", "discovery_label": "Found via",
            "duplicate_count": st.column_config.NumberColumn("Reports merged", help="Distinct articles merged into this record."),
        })
    st.download_button("Download filtered records (CSV)", R.drop(columns=["published", "deadline_dt", "link"], errors="ignore")
                       .to_csv(index=False).encode(), "ai_policy_records_filtered.csv", "text/csv")


# ----------------------------------------------------------------------------- trends tab
with tab_trend:
    excl_api_only = st.checkbox("Exclude records found only through news APIs", value=True,
                                help="GNews and NewsAPI free tiers only reach back ~30 days, which would inflate the latest month.")
    T = A[A["published"].notna()]
    if excl_api_only:
        T = T[~T["discovery_sources"].isin(["gnews", "newsapi", "gnews|newsapi"])]
    if T.empty:
        st.info("No dated records match the current filters.")
    else:
        T = T.assign(month=T["published"].dt.to_period("M").dt.to_timestamp())
        piv = T.pivot_table(index="month", columns="category", values="record_id", aggfunc="count", fill_value=0)
        fig = go.Figure()
        for c in CATEGORY_ORDER:
            if c in piv:
                fig.add_trace(go.Bar(x=piv.index, y=piv[c], name=CATEGORY_LABELS[c], marker_color=CATEGORY_COLORS[c],
                                     marker_line=dict(color="#ffffff", width=2),
                                     hovertemplate="%{x|%b %Y}<br>" + CATEGORY_LABELS[c] + ": %{y}<extra></extra>"))
        fig.update_layout(barmode="stack", height=430, margin=dict(l=0, r=0, t=10, b=0), bargap=0.25,
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          legend=dict(orientation="h", y=-0.15, font=dict(size=11, color=INK2), traceorder="normal"),
                          xaxis=dict(tickformat="%b %Y", tickfont=dict(color=INK2), showgrid=False),
                          yaxis=dict(title=dict(text="Activities (by source publication month)", font=dict(size=11, color=INK2)),
                                     gridcolor=GRID, tickfont=dict(color=INK2), zeroline=False),
                          hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("Months are when sources were published, not when activities occurred. The collection window covers "
                   "12 months; the first and last months may be partial. Volume reflects media attention as well as activity.")
        with st.expander("Table view"):
            st.dataframe(piv.rename(columns=CATEGORY_LABELS).rename_axis("Month").reset_index()
                         .assign(Month=lambda d: d["Month"].dt.strftime("%b %Y")), hide_index=True, use_container_width=True)


# ----------------------------------------------------------------------------- institutions & sources
with tab_inst:
    c1, c2 = st.columns([1.1, 1], gap="large")
    with c1:
        st.markdown("### Institutions")
        st.caption("Institutions from the project's seed registry that are named in records (state-consistent mentions only).")
        rows = []
        for _, r in A[A["institutions"] != ""].iterrows():
            for inst in r["institutions"].split("|"):
                rows.append({"Institution": inst, "State / UT": r["state"], "category": r["category"]})
        if rows:
            it = pd.DataFrame(rows)
            agg = it.groupby(["Institution", "State / UT"]).agg(
                Records=("category", "size"),
                Categories=("category", lambda s: ", ".join(CATEGORY_LABELS[c] for c in sorted(set(s))))).reset_index()
            st.dataframe(agg.sort_values("Records", ascending=False), hide_index=True, use_container_width=True, height=420)
        else:
            st.info("No registry institutions are named in the filtered records.")
    with c2:
        st.markdown("### Sources")
        src = A.groupby(["source_name"]).agg(Records=("record_id", "size"), Type=("source_type", "first"),
                                             Status=("verification_label", lambda s: s.mode().iat[0])).reset_index()
        type_labels = {"government": "Government", "academic": "Academic", "think_tank": "Think tank",
                       "established_media": "Established media", "other_media": "Unclassified publisher"}
        st.dataframe(src.assign(Type=src["Type"].map(type_labels)).rename(columns={"source_name": "Publisher",
                                                                                  "Status": "Typical status"})
                     .sort_values("Records", ascending=False), hide_index=True, use_container_width=True, height=300)
        st.markdown("**Link types and discovery channels** (filtered records)")
        lt = A["url_label"].value_counts().rename_axis("Link type").reset_index(name="Records")
        st.dataframe(lt, hide_index=True, use_container_width=True)
        ch = (A["discovery_sources"].str.split("|").explode().map(DISCOVERY_LABELS).value_counts()
              .rename_axis("Found via").reset_index(name="Records (a record can have several)"))
        st.dataframe(ch, hide_index=True, use_container_width=True)
    st.markdown("### Research coverage by state / UT")
    st.caption("How much the discovery queries retrieved for each state versus what passed screening. A low retrieval "
               "count with no records is an information gap, not evidence of absence.")
    if not cov.empty:
        cv = cov.copy()
        cv["evidence_status"] = cv["evidence_status"].map(EVIDENCE_LABELS).fillna(cv["evidence_status"])
        st.dataframe(cv[["state", "state_type", "raw_items_retrieved_for_state_queries", "records", "distinct_publishers",
                         "primary_source_records", "corroborated_records", "categories_covered", "evidence_status"]]
                     .rename(columns={"state": "State / UT", "state_type": "Type",
                                      "raw_items_retrieved_for_state_queries": "Items retrieved", "records": "Records",
                                      "distinct_publishers": "Publishers", "primary_source_records": "Primary",
                                      "corroborated_records": "Corroborated", "categories_covered": "Categories",
                                      "evidence_status": "Evidence status (all data)"}),
                     hide_index=True, use_container_width=True, height=360)


# ----------------------------------------------------------------------------- opportunities
with tab_opp:
    st.markdown("### Fellowships, internships, workshops and events")
    st.markdown('<div class="note">Detected automatically from news and feeds: an opportunity type (fellowship, internship, '
                'workshop, hackathon, conference…) plus a forward-looking cue (applications open, apply by, to host…). '
                'Always confirm eligibility and dates on the organiser\'s own page. Deadlines are shown only when stated '
                'in the source; many listings may already have closed.</div>', unsafe_allow_html=True)
    if O.empty:
        st.info("No opportunities match the current filters.")
    else:
        types = sorted(O["opportunity_type"].unique())
        pick = st.segmented_control("Type", types, selection_mode="multi", format_func=lambda t: t.replace("_", " ").title())
        OV = O[O["opportunity_type"].isin(pick)] if pick else O
        OV = OV.sort_values("published", ascending=False)
        today = pd.Timestamp(summary.get("run_date")) if summary.get("run_date") else pd.Timestamp.today().normalize()
        for _, r in OV.iterrows():
            dl = (f'Deadline {r["deadline_dt"]:%d %b %Y}' + (" (passed)" if r["deadline_dt"] < today else "")
                  if pd.notna(r["deadline_dt"]) else "Deadline not stated")
            pub = r["published"].strftime("%d %b %Y") if pd.notna(r["published"]) else "unknown"
            head = (f'<a href="{r["link"]}" target="_blank" rel="noopener">{r["title"]}</a>' if r["link"] else r["title"])
            desc = f'<div style="font-size:0.88rem;color:{INK2}">{r["description_shown"]}</div>' if r["description_shown"] else ""
            st.markdown(f'<div class="rec"><span class="pill">{r["opportunity_type"].replace("_", " ")}</span>'
                        f'<span class="pill">{r["state"]}</span>{head}{desc}<div class="meta">{r["source_name"]} · published {pub} · '
                        f'{dl} · <b>{r["verification_label"]}</b> · {r["url_label"]}</div></div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------- about
with tab_about:
    c1, c2 = st.columns([1.3, 1], gap="large")
    with c1:
        st.markdown("### How to read this data")
        st.markdown("""
- **Scope.** A record is kept when it is about AI, can be tied to a state or UT from its text, involves a public actor
  (government, court, police, mission, university, research institute) or a state-level AI investment, and describes an
  activity in one of six categories. Everything rejected is kept, with a reason, in `excluded_records.csv`.
- **Duplicates.** Reports of the same announcement by different outlets are merged into one record; `duplicates.csv`
  shows every merge.
- **Evidence status** describes support in the sources held, not truth:
  *Primary source* (published by government or an academic institution), *Corroborated* (2+ publishers),
  *Single secondary source*, *Unverified* (unrecognised publisher). No record has been manually fact-checked.
- **Links.** *Direct publisher link* points to the article. *Google News redirect* is the link Google News RSS provides;
  the publisher is named alongside. Neither link type is a verification.
- **Dates** are source publication dates. Event / announcement dates are not determined.
- **Descriptions** are shown only when the publisher supplied one. Many records have only a headline, and a headline is
  not presented as a summary.
- **Counts** reflect English-language media coverage and the discovery queries used; they are not a ranking of states.
""")
        st.markdown("Methodology and limitations: `docs/methodology.md`, `docs/limitations.md`.")
    with c2:
        st.markdown("### Downloads")
        for label, name, mime in [("Activities (CSV)", "activities.csv", "text/csv"),
                                  ("Opportunities (CSV)", "opportunities.csv", "text/csv"),
                                  ("Workbook (XLSX)", "ai_policy_activity.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                                  ("Excluded items with reasons (CSV)", "excluded_records.csv", "text/csv"),
                                  ("Duplicate merges (CSV)", "duplicates.csv", "text/csv"),
                                  ("Source registry (CSV)", "source_registry.csv", "text/csv")]:
            b = file_bytes(name)
            if b:
                st.download_button(label, b, name, mime, use_container_width=True)
        if summary:
            st.markdown("### This dataset")
            st.markdown(f"- Collected: **{summary.get('run_date', '—')}**\n"
                        f"- Raw items screened: **{summary.get('raw_entries', 0):,}**\n"
                        f"- Published: **{summary.get('published_activities', 0):,}** activities, "
                        f"**{summary.get('published_opportunities', 0):,}** opportunities\n"
                        f"- Excluded with a reason: **{summary.get('excluded', 0):,}**")
