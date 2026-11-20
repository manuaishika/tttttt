"""Presentation helpers: styles, the map, record lists and the record detail view.

Nothing here computes or alters findings; it formats records from data/processed.
"""
from __future__ import annotations

import html
from functools import partial

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.data import (CATEGORY_LABELS, CATEGORY_ORDER, DISCOVERY_LABELS, LOCATION_BASIS_LABELS, REGION_NAMES,
                            REGION_POINT, STAGE_LABELS, STAGE_ORDER)

# Restrained palette: navy/blue/neutral. Sequential ramp validated (one hue, light -> dark).
NAVY, BLUE = "#0f2747", "#1c5cab"
INK, INK2, MUTED, RULE, SURFACE = "#14171c", "#4a5160", "#7a808c", "#e3e6ea", "#f6f7f9"
SEQ = ["#dbe8f8", "#b7d3f6", "#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d2a4f"]
NO_EVIDENCE = "#eceef1"

CSS = f"""
<style>
  .block-container {{padding-top: 1.4rem; padding-bottom: 4rem; max-width: 1360px;}}
  [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{display: none;}}
  h1, h2, h3 {{color: {NAVY}; letter-spacing: -0.01em;}}
  h1 {{font-size: 1.55rem !important; font-weight: 700 !important; margin: 0 !important; padding: 0 !important;}}
  h2 {{font-size: 1.25rem !important; font-weight: 650 !important; margin-top: 0.4rem !important;}}
  h3 {{font-size: 1.02rem !important; font-weight: 650 !important;}}
  .eyebrow {{text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.72rem; color: {MUTED}; font-weight: 600;}}
  .lede {{color: {INK2}; font-size: 0.95rem; margin: 0.25rem 0 0.2rem 0; max-width: 62rem; line-height: 1.5;}}
  .muted {{color: {MUTED}; font-size: 0.82rem;}}
  .note {{color: {INK2}; font-size: 0.85rem; line-height: 1.5; border-left: 3px solid {RULE}; padding: 0.1rem 0 0.1rem 0.8rem; margin: 0.5rem 0 0.9rem 0;}}
  .rule {{border-top: 1px solid {RULE}; margin: 1.2rem 0 1rem 0;}}
  .stats {{display: flex; flex-wrap: wrap; gap: 0.6rem 2.6rem; padding: 0.9rem 0 0.4rem 0; border-top: 1px solid {RULE}; border-bottom: 1px solid {RULE};}}
  .stat .v {{font-size: 1.55rem; font-weight: 650; color: {NAVY}; line-height: 1.2;}}
  .stat .l {{font-size: 0.78rem; color: {INK2}; max-width: 12rem; line-height: 1.35;}}
  .tbl {{width: 100%; border-collapse: collapse; font-size: 0.86rem;}}
  .tbl td, .tbl th {{padding: 0.32rem 0.4rem; border-bottom: 1px solid {RULE}; text-align: left; vertical-align: top;}}
  .tbl th {{color: {MUTED}; font-weight: 600; font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.04em;}}
  .tbl td.n {{text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap;}}
  .tbl td.none {{color: {MUTED};}}
  .rec {{border-bottom: 1px solid {RULE}; padding: 0.6rem 0;}}
  .rec a, .rec .t {{color: {INK}; text-decoration: none; font-weight: 600; font-size: 0.93rem; line-height: 1.4;}}
  .rec a:hover {{text-decoration: underline; color: {BLUE};}}
  .rec .d {{font-size: 0.86rem; color: {INK2}; margin-top: 0.2rem; line-height: 1.45;}}
  .rec .m {{color: {MUTED}; font-size: 0.78rem; margin-top: 0.2rem;}}
  .tag {{display: inline-block; font-size: 0.72rem; padding: 0.02rem 0.45rem; border-radius: 3px; background: {SURFACE};
        color: {INK2}; border: 1px solid {RULE}; margin-right: 0.3rem; white-space: nowrap;}}
  .tag.strong {{background: #e8f0fb; border-color: #c9dbf3; color: {NAVY};}}
  .tag.warn {{background: #fff6e5; border-color: #f2dfb5; color: #6b4e00;}}
  .tag.bad {{background: #f6eeee; border-color: #e6cfcf; color: #6e2b2b;}}
  .detail h3 {{font-size: 1.12rem !important; line-height: 1.4; margin: 0.2rem 0 0.6rem 0;}}
  .kv {{display: grid; grid-template-columns: 9.5rem 1fr; gap: 0.35rem 0.9rem; font-size: 0.86rem; margin-top: 0.6rem;}}
  .kv .k {{color: {MUTED};}}
  .kv .v {{color: {INK}; overflow-wrap: anywhere;}}
  .desc {{background: {SURFACE}; border-left: 3px solid {BLUE}; padding: 0.6rem 0.8rem; font-size: 0.9rem; color: {INK}; line-height: 1.5;}}
  .desc.none {{border-left-color: {RULE}; color: {INK2}; font-style: italic;}}
  div[data-testid="stButtonGroup"] > div {{flex-wrap: wrap; row-gap: 0.35rem;}}
  @media (max-width: 700px) {{
    .block-container {{padding-left: 0.9rem; padding-right: 0.9rem;}}
    .stats {{gap: 0.5rem 1.4rem;}} .stat .v {{font-size: 1.25rem;}}
    .kv {{grid-template-columns: 1fr;}} .kv .k {{margin-top: 0.4rem;}}
  }}
</style>"""


def esc(s) -> str:
    return html.escape(str(s or ""))


def stats_html(items: list[tuple[str, str]]) -> str:
    return '<div class="stats">' + "".join(
        f'<div class="stat"><div class="v">{esc(v)}</div><div class="l">{esc(l)}</div></div>' for v, l in items) + "</div>"


def evidence_tag(status: str, label: str) -> str:
    cls = "strong" if status in ("primary_source", "corroborated") else ("bad" if status == "unverified" else "")
    return f'<span class="tag {cls}">{esc(label)}</span>'


def record_row_html(r: pd.Series, show_state: bool = True) -> str:
    title = esc(r["title"] or "(untitled)")
    head = (f'<a href="{esc(r["link"])}" target="_blank" rel="noopener">{title}</a>' if r["link"]
            else f'<span class="t">{title}</span>')
    date = r["published"].strftime("%d %b %Y") if pd.notna(r["published"]) else "date unknown"
    desc = f'<div class="d">{esc(r["description_full"][:260])}{"…" if len(r["description_full"]) > 260 else ""}</div>' \
        if r["description_full"] else ""
    where = f'{esc(r["state"])} · ' if show_state else ""
    return (f'<div class="rec">{head}{desc}<div class="m">{where}{esc(r["source_name"] or "unknown publisher")} · '
            f'published {date} · {esc(r["category_label"])}</div>'
            f'<div style="margin-top:0.25rem">{evidence_tag(r["verification_status"], r["verification_label"])}'
            f'<span class="tag">{esc(r["stage_label"])}</span><span class="tag">{esc(r["url_label"])}</span></div></div>')


def brief_item_html(i: int, r: pd.Series) -> str:
    actor = esc(r["actor_display"]) if r["actors"] else '<span style="color:#7a808c">Actor not identified in headline</span>'
    title = esc(r["title"])
    head = f'<a href="{esc(r["link"])}" target="_blank" rel="noopener">{title}</a>' if r["link"] else title
    date = r["published"].strftime("%d %b %Y") if pd.notna(r["published"]) else "date unknown"
    where = r["state"] if r["geographic_scope"] != "multi_state" else r["states_mentioned"].replace("|", ", ")
    stage = (f'{r["activity_stage_label"]} ({r["stage_confidence"]} confidence)' if r["activity_stage"] != "undetermined"
             else "stage undetermined")
    return (f'<div class="rec"><div style="display:flex;gap:0.6rem"><div class="muted" style="min-width:1.2rem">{i}.</div>'
            f'<div><div style="font-size:0.84rem;color:#0f2747;font-weight:600">{actor}</div>{head}'
            f'<div class="m">{esc(where)} · {esc(r["category_label"])} · {esc(stage)} · source published {date} · '
            f'{esc(r["source_name"])} · {esc(r["verification_label"])}</div></div></div></div>')


# --------------------------------------------------------------------------- map
MAP_METRICS = {
    "records": ("Reporting volume", "records found",
                "Number of distinct activities found in this collection (after merging duplicate reports). "
                "It measures reporting volume in English-language sources, not the amount of activity."),
    "categories": ("Category breadth", "of 6 categories with ≥1 record",
                   "How many of the six activity categories have at least one record. Breadth of what was reported, "
                   "not depth or quality."),
    "strong": ("Well-sourced records", "primary-source or corroborated records",
               "Records published by an official source or reported by two or more publishers."),
}


def state_metrics(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[df["state"].isin(REGION_NAMES)]
    g = sub.groupby("state")
    m = pd.DataFrame({"records": g.size(), "categories": g["category"].nunique(),
                      "strong": g["strong_evidence"].sum()}).reindex(REGION_NAMES).fillna(0).astype(int)
    return m.rename_axis("state").reset_index()


def build_map(metric: str, m: pd.DataFrame, focus: str | None, geojson: dict | None,
              hot: pd.DataFrame | None = None, height: int = 680) -> go.Figure:
    _, unit, _ = MAP_METRICS[metric]
    label = MAP_METRICS[metric][0]
    has, none = m[m[metric] > 0], m[m[metric] == 0]
    keep = dict(selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)))
    fig = go.Figure()
    if geojson:
        fig.add_trace(go.Choropleth(
            geojson=geojson, featureidkey="properties.state", locations=none["state"], z=[0] * len(none),
            colorscale=[[0, NO_EVIDENCE], [1, NO_EVIDENCE]], showscale=False, marker_line_color="#ffffff",
            marker_line_width=0.8, customdata=none["state"], name="none", **keep,
            hovertemplate="<b>%{customdata}</b><br>No records in this collection<br>"
                          "<i>not evidence that no activity exists</i><extra></extra>"))
        fig.add_trace(go.Choropleth(
            geojson=geojson, featureidkey="properties.state", locations=has["state"], z=has[metric],
            colorscale=[[i / (len(SEQ) - 1), c] for i, c in enumerate(SEQ)], zmin=0,
            marker_line_color="#ffffff", marker_line_width=0.8, customdata=has["state"], **keep,
            colorbar=dict(orientation="h", x=0.5, xanchor="center", y=-0.01, yanchor="top", len=0.55, thickness=9,
                          outlinewidth=0, tickfont=dict(size=10, color=INK2),
                          title=dict(text=f"{label} ({unit})", side="top", font=dict(size=11, color=INK2))),
            hovertemplate="<b>%{customdata}</b><br>%{z} " + unit + "<extra>click to open profile</extra>"))
        if focus in REGION_NAMES:
            val = int(m.loc[m["state"] == focus, metric].iloc[0])
            fig.add_trace(go.Choropleth(
                geojson=geojson, featureidkey="properties.state", locations=[focus], z=[0],
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False,
                marker_line_color=NAVY, marker_line_width=3, customdata=[focus], **keep,
                hovertemplate=f"<b>{focus}</b> (selected)<br>{val} {unit}<extra></extra>"))
    else:  # transparent fallback: approximate state points, never invented shapes
        pts = m.assign(lat=m["state"].map(lambda s: REGION_POINT[s][0]), lon=m["state"].map(lambda s: REGION_POINT[s][1]))
        fig.add_trace(go.Scattergeo(
            lat=pts["lat"], lon=pts["lon"], customdata=pts["state"], mode="markers", text=pts[metric].astype(str),
            marker=dict(size=8 + pts[metric].clip(upper=100) ** 0.5 * 3.5, color=BLUE, line=dict(color="#fff", width=1.5)),
            hovertemplate="<b>%{customdata}</b><br>%{text} " + unit + " (approximate location)<extra></extra>", **keep))
    if hot is not None and not hot.empty:
        fig.add_trace(go.Scattergeo(
            lat=hot["lat"], lon=hot["lon"], mode="markers", customdata=hot["state"], text=hot["place"],
            hovertext=hot["records"].astype(str) + " located record(s)",
            marker=dict(size=6 + hot["records"].clip(upper=40) ** 0.5 * 2.6, color="#ffffff", opacity=0.95,
                        line=dict(color=NAVY, width=1.6)),
            hovertemplate="<b>%{text}</b> · %{customdata}<br>%{hovertext}<extra></extra>", **keep))
    fig.update_geos(visible=False, projection_type="mercator", lataxis_range=[6.2, 37.4], lonaxis_range=[68, 97.6],
                    bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=40), paper_bgcolor="rgba(0,0,0,0)",
                      showlegend=False, clickmode="event+select", dragmode=False,
                      hoverlabel=dict(bgcolor="#ffffff", bordercolor=RULE, font=dict(color=INK, size=12)))
    return fig


def hotspots(df: pd.DataFrame) -> pd.DataFrame:
    located = df[df["lat"].notna() & df["lon"].notna()].copy()
    if located.empty:
        return pd.DataFrame()
    located["place"] = located["institutions"].str.split("|").str[0].where(located["institutions"] != "", located["city"])
    return located.groupby(["place", "state", "lat", "lon"]).size().rename("records").reset_index()


def hbar(labels: list[str], values: list[int], height: int, unit: str, total: int | None = None) -> go.Figure:
    text = [f"{v}" + (f"  ({v / total:.0%})" if total else "") for v in values]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker=dict(color=BLUE, cornerradius=3),
                           text=text, textposition="outside", cliponaxis=False,
                           textfont=dict(color=INK2, size=11), hovertemplate="%{y}: %{x} " + unit + "<extra></extra>"))
    fig.update_layout(height=height, margin=dict(l=0, r=60, t=4, b=0), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", bargap=0.38,
                      xaxis=dict(visible=False, range=[0, max(max(values, default=1), 1) * 1.25]),
                      yaxis=dict(autorange="reversed", tickfont=dict(size=12, color=INK2)))
    return fig


# --------------------------------------------------------------------------- detail
def render_detail(r: pd.Series, dups: pd.DataFrame) -> None:
    date = r["published"].strftime("%d %B %Y") if pd.notna(r["published"]) else "unknown"
    st.markdown(f'<div class="detail"><div class="eyebrow">{esc(r["category_label"])} · {esc(r["sector_label"])}</div>'
                f'<h3>{esc(r["title"])}</h3></div>', unsafe_allow_html=True)
    st.markdown(f'{evidence_tag(r["verification_status"], r["verification_label"])}'
                f'<span class="tag">Stage: {esc(r["activity_stage_label"])}</span>'
                f'<span class="tag">Headline wording: {esc(r["stage_label"])}</span>'
                f'<span class="tag">{esc(r["url_label"])}</span>', unsafe_allow_html=True)
    if r["description_full"]:
        st.markdown(f'<div class="desc" style="margin-top:0.7rem"><div class="eyebrow" style="margin-bottom:0.2rem">'
                    f'Publisher description</div>{esc(r["description_full"])}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="desc none" style="margin-top:0.7rem">No description available: this record has only '
                    'a headline. Open the source to read the article.</div>', unsafe_allow_html=True)
    if r["link"]:
        st.link_button("Open source ↗", r["link"], use_container_width=False)
    if r["url_type"] == "google_news_redirect":
        link_note = ("Google News redirect: opens the article via news.google.com. The original publisher URL was not "
                     "provided by the feed and is not stored.")
    else:
        link_note = "Direct link to the publisher's article."
    insts = r["institutions"].replace("|", ", ") or "none named from the registry"
    others = [x for x in r["corroborating_sources"].split("|") if x]
    rows = [
        ("State / UT", f'{r["state"]}' + (f' · {r["city"]}' if r["city"] else "")),
        ("Why this state", r["state_evidence"]),
        ("Geographic scope", r["scope_label"] + (f' (states named: {r["states_mentioned"].replace("|", ", ")})'
                                                 if r["geographic_scope"] == "multi_state" else "")),
        ("Location basis", LOCATION_BASIS_LABELS.get(r["location_basis"], "not recorded")),
        ("Actors named", (f'{r["actor_display"]} ({r["actor_class_display"]})' if r["actors"]
                          else "No actor identifiable from the headline")),
        ("Actor location", r["actor_location"].replace("|", "; ") or "Not established"),
        ("Activity stage", r["activity_stage_label"] + (f' (confidence {r["stage_confidence"]}): {r["stage_basis"]}'
                                                        if r["stage_confidence"] else f': {r["stage_basis"] or "not assessed"}')),
        ("Institutions", insts),
        ("Published", f'{date} (source publication date; precision: {r["date_precision"] or "unknown"})'),
        ("Event date", "Not determined: the date the activity happened is not extracted"),
        ("Publisher", f'{r["source_name"]} · {r["source_type_label"]}'),
        ("Evidence status", f'{r["verification_label"]}: {r["verification_basis"]}'),
        ("Link", link_note),
        ("Other publishers", ", ".join(others) if others else "none in this collection"),
        ("Found via", r["discovery_label"]),
        ("Classification", f'{r["category_label"]} (rule confidence: {r["category_confidence"] or "n/a"}); headline '
                           f'wording cue: {r["stage_label"]} (verbs only, not a maturity assessment)'),
        ("Record ID", f'{r["record_id"]} · cluster {r["cluster_id"]} · raw ref {r["raw_ref"]}'),
        ("Collected", r["collected_at"] or "unknown"),
    ]
    if r.get("opportunity_type"):
        rows.insert(3, ("Opportunity type", r["opportunity_type"].replace("_", " ")))
    st.markdown('<div class="kv">' + "".join(f'<div class="k">{esc(k)}</div><div class="v">{esc(v)}</div>' for k, v in rows)
                + "</div>", unsafe_allow_html=True)
    merged = dups[dups["record_id"] == r["record_id"]] if not dups.empty else pd.DataFrame()
    if len(merged) > 1:
        with st.expander(f"{len(merged)} reports merged into this record"):
            for _, d in merged.iterrows():
                t = esc(d["title"])
                lk = f'<a href="{esc(d["source_url"])}" target="_blank" rel="noopener">{t}</a>' if d["source_url"] else t
                st.markdown(f'<div class="rec">{lk}<div class="m">{esc(d["source_name"])} · {esc(d["published_date"])} · '
                            f'{esc(DISCOVERY_LABELS.get(d.get("discovery_source", ""), d.get("discovery_source", "")))} · '
                            f'{"canonical" if d["role"] == "canonical" else "merged duplicate"}</div></div>',
                            unsafe_allow_html=True)


def record_browser(df: pd.DataFrame, dups: pd.DataFrame, key: str, height: int = 520) -> None:
    """Table of records (left) with a detail panel (right) for the selected row."""
    if df.empty:
        st.info("No records match.")
        return
    view = df.sort_values("published", ascending=False).reset_index(drop=True)
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        ev = st.dataframe(
            view.assign(Published=view["published"].dt.strftime("%Y-%m-%d").fillna("unknown"))[
                ["Published", "state", "title", "verification_label", "category_label"]],
            hide_index=True, use_container_width=True, height=height, on_select="rerun",
            selection_mode="single-row", key=key,
            column_config={"state": st.column_config.TextColumn("State / UT", width="small"),
                           "title": st.column_config.TextColumn("Headline", width="large"),
                           "category_label": st.column_config.TextColumn("Category", width="medium"),
                           "verification_label": st.column_config.TextColumn("Evidence", width="small"),
                           "Published": st.column_config.TextColumn("Published", width="small")})
    with right:
        rows = ev.selection.rows if ev is not None and hasattr(ev, "selection") else []
        if rows:
            render_detail(view.iloc[rows[0]], dups)
        else:
            st.markdown('<div class="note">Select a row to open the record: headline, state attribution, category, '
                        'publication date, publisher, original link, evidence status, description (where the publisher '
                        'supplied one) and full provenance.</div>', unsafe_allow_html=True)


def category_table_html(sub: pd.DataFrame) -> str:
    """Per-category counts and stage-cue mix for a set of records (e.g. one state)."""
    head = ("<tr><th>Area</th><th class='n'>Records</th>" + "".join(
        f"<th class='n'>{esc(STAGE_LABELS[s].split(' / ')[0])}</th>" for s in STAGE_ORDER) + "<th>Most recent</th></tr>")
    body = []
    for c in CATEGORY_ORDER:
        x = sub[sub["category"] == c]
        if x.empty:
            body.append(f"<tr><td>{esc(CATEGORY_LABELS[c])}</td><td class='n none'>0</td>"
                        + "".join("<td class='n none'>–</td>" for _ in STAGE_ORDER)
                        + "<td class='none'>none found in this collection</td></tr>")
            continue
        latest = x.sort_values("published", ascending=False).iloc[0]
        stages = x["stage_cue"].value_counts()
        body.append(f"<tr><td>{esc(CATEGORY_LABELS[c])}</td><td class='n'>{len(x)}</td>"
                    + "".join(f"<td class='n'>{int(stages.get(s, 0)) or '–'}</td>" for s in STAGE_ORDER)
                    + f"<td>{esc(latest['title'][:110])}{'…' if len(latest['title']) > 110 else ''}</td></tr>")
    return f"<table class='tbl'>{head}{''.join(body)}</table>"


def select_callback(key: str, target: str = "focus_state"):
    """Plotly on_select callback factory: copy the clicked state into session state."""
    return partial(_on_map_select, key, target)


def _on_map_select(key: str, target: str) -> None:
    sel = st.session_state.get(key)
    pts = (sel or {}).get("selection", {}).get("points", []) if sel else []
    for p in pts:
        name = p.get("customdata") or p.get("location")
        if isinstance(name, list):
            name = name[0]
        if name in REGION_NAMES:
            st.session_state[target] = name
            return
