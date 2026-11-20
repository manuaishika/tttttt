"""End-to-end processing: raw snapshot -> validated datasets + audit trail.

    python -m src.pipeline                      # process all snapshots in data/raw (RSS + APIs)
    python -m src.pipeline --raw <file.jsonl>…  # reproduce from specific snapshots offline
    python -m src.pipeline --collect            # collect first, then process
    python -m src.pipeline --check-seeds        # also probe official seed sites' reachability

Outputs (data/processed/):
    activities.csv, opportunities.csv, ai_policy_activity.xlsx   - the deliverable datasets
    excluded_records.csv     - every rejected raw item with a reason code (transparency)
    duplicates.csv           - how raw items were collapsed into records (traceability)
    source_registry.csv      - every publisher seen + reviewed seed sources
    state_coverage.csv       - per state/UT evidence & research-coverage summary
    run_summary.json         - counts for the run
"""
from __future__ import annotations
import argparse, csv, hashlib, html, json, re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import schema as S
from .classify import (classify, screen, screen_after_classification, state_is_subject)
from .collect import ROOT, collect, load_config
from .deduplicate import canonical_url, cluster, link_opportunities, normalize_title, pick_canonical
from .normalize import (city_coords, extract_cities, extract_institutions, extract_states, normalize_date)
from .reference import REGIONS, REGION_BY_NAME
from .stage import stage_cue
from .sources import TIER, check_reachability, classify_source, domain_of, verification_for
from .validate import validate_records

PROCESSED = ROOT / "data" / "processed"


# ------------------------------------------------------------------ helpers ---
def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", html.unescape(s or ""))
    return re.sub(r"\s+", " ", s).strip()


def _first_sentence(s: str, limit: int = 280) -> str:
    s = _strip_html(s)
    m = re.match(r"(.+?[.!?])(\s|$)", s)
    out = m.group(1) if m else s
    return out[:limit].rstrip() + ("…" if len(out) > limit else "")


def clean_title(title: str, publisher: str | None) -> str:
    t = html.unescape(title or "").strip()
    if publisher:
        t = re.sub(r"\s+[-|–—]\s+" + re.escape(publisher) + r"\s*$", "", t, flags=re.I)
    return t.strip()


def load_raw(path: Path) -> list[dict]:
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def all_raw(raw_dir: Path) -> list[Path]:
    """Every snapshot (RSS and API). Processing the union is safe: exact-URL repeats and
    cross-outlet duplicates are collapsed, and the time window drops stale items."""
    files = sorted(raw_dir.glob("*/*.jsonl"))
    if not files:
        raise SystemExit(f"no raw snapshots in {raw_dir}; run with --collect")
    return files


def discovery_source(e: dict) -> str:
    """Older snapshots predate the api_source field; derive it from the collector kind."""
    if e.get("api_source"):
        return e["api_source"]
    return "google_news_rss" if e.get("kind") == "google_news" else "direct_feed"


def url_type_of(link: str) -> str:
    return "google_news_redirect" if "news.google.com" in (link or "") else "publisher_direct"


def assign_state(title: str, desc: str, hint: str | None) -> dict | None:
    """Decide the state from the HEADLINE first (state names, then institutions, then cities),
    and only fall back to the description when the headline has no anchor at all.
    The query's state is NOT evidence on its own (a Kerala query can return a Gujarat story)."""
    for text, where in ((title, "headline"), (f"{title}. {desc}", "description")):
        if not text.strip():
            continue
        found = _anchor(text, hint)
        if found:
            if where == "description":
                found["evidence"] += " [from publisher description]"
            return found
        if not desc:
            break
    return None


def _anchor(text: str, hint: str | None) -> dict | None:
    states = extract_states(text)
    insts = extract_institutions(text)
    cities = extract_cities(text)
    if states:
        names = [s for s, _ in states]
        pick = hint if hint in names else names[0]
        ev = next(e for s, e in states if s == pick)
        note = f"text: '{ev}'" + (f"; also mentions {', '.join(n for n in names if n != pick)}" if len(names) > 1 else "")
        return {"state": pick, "evidence": note, "ev_text": ev, "insts": insts, "cities": cities, "basis": "text"}
    if insts:
        i = insts[0]
        return {"state": i.state, "evidence": f"institution: {i.name} ({i.state})", "ev_text": None,
                "insts": insts, "cities": cities, "basis": "institution"}
    if cities:
        c, st = cities[0]
        return {"state": st, "evidence": f"city: {c} ({st})", "ev_text": None, "insts": insts,
                "cities": cities, "basis": "city"}
    return None


def geo_for(state: str, insts, cities) -> tuple[str, str, str, str]:
    """(city, lat, lon, precision) using ONLY registry-backed coordinates consistent with the state."""
    city = next((c for c, st in cities if st == state), "")
    for i in insts:
        if i.state == state:
            return city or i.city, f"{i.lat:.4f}", f"{i.lon:.4f}", "institution"
    if city:
        xy = city_coords(city)
        if xy:
            return city, f"{xy[0]:.4f}", f"{xy[1]:.4f}", "city"
    return city, "", "", "state" if state != S.PAN_INDIA else "none"


# -------------------------------------------------------------- main process ---
def process(raw_paths: list[Path] | Path, out_dir: Path, today: date | None = None, window_days: int = 365,
            check_seeds: bool = False) -> dict:
    today = today or datetime.now(timezone.utc).date()
    raw_paths = [raw_paths] if isinstance(raw_paths, Path) else list(raw_paths)
    raw = [e for p in raw_paths for e in load_raw(p)]
    for e in raw:
        e["api_source"] = discovery_source(e)
    excluded: list[dict] = []
    cands: list[dict] = []
    seen_raw = Counter()

    def exclude(e: dict, reason: str, title: str | None = None):
        excluded.append({"exclusion_reason": reason, "title": title or e.get("title"), "source_name": e.get("source_name"),
                         "source_url": e.get("link"), "hint_state": e.get("hint_state") or "",
                         "published_raw": e.get("published_raw"), "query_id": e.get("query_id"), "raw_ref": e.get("raw_ref")})

    for e in raw:
        pub_name = e.get("source_name")
        title = clean_title(e.get("title"), pub_name)
        desc = _strip_html(e.get("description", ""))
        if not title or not e.get("link"):
            exclude(e, "missing_title_or_url"); continue
        seen_raw[e["query_id"]] += 1
        d = normalize_date(e.get("published_raw"), today)
        if d.iso and (today - date.fromisoformat(d.iso)).days > window_days + 30:
            exclude(e, "outside_time_window", title); continue
        ok, reason = screen(title, desc)
        if not ok:
            exclude(e, reason, title); continue
        c = classify(title, date.fromisoformat(d.iso) if d.iso else None, context=desc)
        st = assign_state(title, desc, e.get("hint_state"))
        pan_india = False
        if st is None:
            if c.record_type == "opportunity" and str(e.get("query_id", "")).startswith("IN:"):
                pan_india = True
            else:
                exclude(e, "state_not_in_text" if e.get("hint_state") else "no_state_anchor", title); continue
        subj = bool(st and st["ev_text"] and state_is_subject(title, st["ev_text"]))
        ok, reason = screen_after_classification(title, desc, c, state_subject=subj or (st is not None and st["basis"] == "institution"))
        if not ok:
            exclude(e, reason, title); continue

        utype = url_type_of(e["link"])
        # For direct links the article's own host is the most reliable publisher identity.
        s_type, s_reason = classify_source(e.get("publisher_url") or (e["link"] if utype == "publisher_direct" else None), pub_name)
        state = S.PAN_INDIA if pan_india else st["state"]
        reg = REGION_BY_NAME.get(state)
        city, lat, lon, gp = ("", "", "", "none") if pan_india else geo_for(state, st["insts"], st["cities"])
        cands.append({
            "state": state, "state_code": reg.code if reg else "", "state_type": reg.kind if reg else "",
            "city": city, "institutions": "|".join(i.name for i in (st["insts"] if st else []) if i.state == state),
            "lat": lat, "lon": lon, "geo_precision": gp,
            "title": title, "summary": _first_sentence(desc) if desc else title,
            "summary_basis": "publisher_description" if desc else "headline_only",
            "source_description": desc[:500],
            "category": c.category, "sector": c.sector, "category_confidence": c.confidence,
            "record_type": c.record_type, "opportunity_type": c.opportunity_type or "",
            "deadline": c.deadline or "", "deadline_status": "stated" if c.deadline else "not_stated",
            "published_date": d.iso or "", "date_precision": d.precision,
            "announcement_date": "", "announcement_date_status": "not_determined",
            "source_name": pub_name or domain_of(e.get("link")), "source_url": e["link"], "url_type": utype,
            "api_source": e["api_source"],
            "publisher_url": e.get("publisher_url") or "", "source_type": s_type, "_source_reason": s_reason,
            "state_evidence": "Pan-India opportunity (no state named)" if pan_india else st["evidence"],
            "matched_query": e.get("query_id"), "raw_ref": e.get("raw_ref"), "collected_at": e.get("fetched_at"),
            "norm_title": normalize_title(title, pub_name), "has_description": bool(desc),
            "url": canonical_url(e["link"]),
        })

    # ---- collapse exact-URL repeats (same article surfaced by several queries) ------
    # These are not "outlets reporting the same news"; counting them would inflate
    # duplicate_count and fake corroboration. First sighting wins; the others are logged.
    first_by_url: dict[str, dict] = {}
    url_repeats = 0
    for c in cands:
        if c["url"] in first_by_url:
            url_repeats += 1
            excluded.append({"exclusion_reason": "exact_url_repeat", "title": c["title"], "source_name": c["source_name"],
                             "source_url": c["source_url"], "hint_state": "", "published_raw": c["published_date"],
                             "query_id": c["matched_query"], "raw_ref": c["raw_ref"]})
        else:
            first_by_url[c["url"]] = c
    cands = list(first_by_url.values())

    # ---- deduplicate across outlets -------------------------------------------------
    items = [{"state": c["state"], "norm_title": c["norm_title"], "published_date": c["published_date"],
              "url": c["url"], "record_type": c["record_type"], "opportunity_type": c["opportunity_type"]} for c in cands]
    labels = link_opportunities(items, cluster(items))
    groups: dict[int, list[dict]] = defaultdict(list)
    for c, lab in zip(cands, labels):
        groups[lab].append(c)

    records, dup_rows = [], []
    for lab, members in groups.items():
        canon = pick_canonical(members)
        publishers = {m["source_name"].casefold() for m in members}
        others = sorted({m["source_name"] for m in members if m["source_name"].casefold() != canon["source_name"].casefold()})
        vs, basis = verification_for(canon["source_type"], len(publishers))
        # corroboration may come from a different source_type than canon (e.g. primary govt + media)
        rid = "r_" + hashlib.sha1(f"{canon['state']}|{canon['norm_title']}|{canon['published_date'][:7]}".encode()).hexdigest()[:12]
        cluster_id = "c_" + hashlib.sha1(str(sorted(m["url"] for m in members)).encode()).hexdigest()[:10]
        rec = {k: v for k, v in canon.items() if not k.startswith("_") and k not in ("norm_title", "has_description", "url", "api_source")}
        if rec["summary_basis"] == "headline_only":
            # borrow a publisher description from another outlet in the same cluster, if any
            donor = next((m for m in members if m["summary_basis"] == "publisher_description"), None)
            if donor:
                rec.update(summary=donor["summary"], summary_basis="publisher_description",
                           source_description=f"[{donor['source_name']}] {donor['source_description']}")
        rec.update(record_id=rid, verification_status=vs, stage_cue=stage_cue(rec["title"]),
                   verification_basis=f"{basis}; source classified via {canon['_source_reason']}",
                   duplicate_count=len(members), corroborating_sources="|".join(others), cluster_id=cluster_id,
                   discovery_sources="|".join(sorted({m["api_source"] for m in members})))
        records.append(rec)
        for m in members:
            dup_rows.append({"cluster_id": cluster_id, "record_id": rid, "role": "canonical" if m is canon else "duplicate",
                             "title": m["title"], "source_name": m["source_name"], "source_url": m["source_url"],
                             "published_date": m["published_date"], "url_type": m["url_type"],
                             "discovery_source": m["api_source"], "raw_ref": m["raw_ref"]})

    # ---- manual opportunity review (a dated annotation; never deletes records) -------
    review_path = ROOT / "config" / "opportunity_review.csv"
    review = {}
    if review_path.exists():
        review = {r["record_id"]: r for r in csv.DictReader(review_path.open())}
    for rec in records:
        if rec["record_type"] == "opportunity":
            rv = review.get(rec["record_id"])
            rec["review_status"] = rv["review_status"] if rv else "not_reviewed"
            rec["review_note"] = rv["review_note"] if rv else ""

    # ---- validate -------------------------------------------------------------------
    valid, rejected, issues = validate_records(records, today)
    for r in rejected:
        excluded.append({"exclusion_reason": r["exclusion_reason"], "title": r["title"], "source_name": r["source_name"],
                         "source_url": r["source_url"], "hint_state": "", "published_raw": r["published_date"],
                         "query_id": r["matched_query"], "raw_ref": r["raw_ref"]})

    activities = sorted([r for r in valid if r["record_type"] == "activity"], key=lambda r: r["published_date"], reverse=True)
    opps = sorted([r for r in valid if r["record_type"] == "opportunity"], key=lambda r: r["published_date"], reverse=True)

    # ---- write ------------------------------------------------------------------------
    out_dir.mkdir(parents=True, exist_ok=True)
    df_a = pd.DataFrame(activities, columns=S.ACTIVITY_COLUMNS)
    df_o = pd.DataFrame(opps, columns=S.OPPORTUNITY_COLUMNS)
    df_a.to_csv(out_dir / "activities.csv", index=False)
    df_o.to_csv(out_dir / "opportunities.csv", index=False)
    pd.DataFrame(excluded).to_csv(out_dir / "excluded_records.csv", index=False)
    pd.DataFrame(dup_rows).to_csv(out_dir / "duplicates.csv", index=False)

    registry = build_source_registry(cands, valid, check_seeds)
    registry.to_csv(out_dir / "source_registry.csv", index=False)
    coverage = build_state_coverage(raw, valid)
    coverage.to_csv(out_dir / "state_coverage.csv", index=False)

    with pd.ExcelWriter(out_dir / "ai_policy_activity.xlsx", engine="openpyxl") as xw:
        df_a.to_excel(xw, sheet_name="activities", index=False)
        df_o.to_excel(xw, sheet_name="opportunities", index=False)
        coverage.to_excel(xw, sheet_name="state_coverage", index=False)
        registry.to_excel(xw, sheet_name="source_registry", index=False)
        pd.DataFrame(S.CATEGORIES.items(), columns=["key", "label"]).to_excel(xw, sheet_name="taxonomy", index=False)

    summary = {
        "run_date": today.isoformat(),
        "raw_files": [str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p) for p in raw_paths],
        "raw_entries": len(raw), "exact_url_repeats_collapsed": url_repeats, "screened_candidates": len(cands), "after_dedup_records": len(records),
        "published_activities": len(activities), "published_opportunities": len(opps),
        "excluded": len(excluded), "exclusion_reasons": dict(Counter(e["exclusion_reason"].split(":")[0] for e in excluded)),
        "validation_warnings": len([i for i in issues if i.severity == "warning"]),
        "verification_status": dict(Counter(r["verification_status"] for r in valid)),
        "states_with_records": len({r["state"] for r in valid if r["state"] != S.PAN_INDIA}),
        "url_type": dict(Counter(r["url_type"] for r in valid)),
        "summary_basis": dict(Counter(r["summary_basis"] for r in valid)),
        "by_discovery_source": source_contribution(raw, cands, valid, rejected),
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def source_contribution(raw, cands, valid, rejected) -> dict:
    """Per discovery channel: raw items, screened candidates (after URL collapse), published
    records it contributed to, records ONLY it found, and records failing validation."""
    out = {}
    for src in S.DISCOVERY_SOURCES:
        ds = lambda r: str(r.get("discovery_sources") or "").split("|")
        out[src] = {
            "raw_items": sum(e["api_source"] == src for e in raw),
            "candidates_after_url_collapse": sum(c["api_source"] == src for c in cands),
            "published_records_contributed_to": sum(src in ds(r) for r in valid),
            "published_records_found_only_by_this_source": sum(ds(r) == [src] for r in valid),
            "records_failing_validation": sum(src in ds(r) for r in rejected),
        }
    return out


def build_source_registry(cands: list[dict], valid: list[dict], check_seeds: bool) -> pd.DataFrame:
    kept = Counter(r["source_name"] for r in valid)
    rows = {}
    for c in cands:
        k = c["source_name"]
        r = rows.setdefault(k, {"source_name": k, "publisher_url": c["publisher_url"], "domain": domain_of(c["publisher_url"]),
                                "source_type": c["source_type"], "source_tier": TIER[c["source_type"]],
                                "classification_reason": c["_source_reason"], "candidate_items": 0})
        r["candidate_items"] += 1
    for k, r in rows.items():
        r["records_in_dataset"] = kept.get(k, 0)
        r["role"] = {"government": "primary source", "academic": "primary source", "think_tank": "secondary (analysis)",
                     "established_media": "secondary (discovery & corroboration)", "other_media": "unverified (discovery only)"}[r["source_type"]]
        r["origin"] = "observed in collection"
    reg = pd.DataFrame(rows.values()).sort_values(["source_tier", "records_in_dataset"], ascending=[True, False])
    seed = pd.read_csv(ROOT / "config" / "seed_sources.csv")
    if check_seeds:
        status = check_reachability(seed["url"].tolist())
        seed["last_check"] = seed["url"].map(status) + f" ({date.today().isoformat()}, from collection environment)"
    seed_rows = pd.DataFrame({
        "source_name": seed["name"], "publisher_url": seed["url"], "domain": seed["url"].map(domain_of),
        "source_type": seed["source_type"], "source_tier": seed["source_type"].map(TIER),
        "classification_reason": "reviewed seed source", "candidate_items": 0, "records_in_dataset": 0,
        "role": seed["relevance"], "origin": "seed list - " + seed["collection_method"]})
    if check_seeds:
        seed_rows["origin"] = seed_rows["origin"] + "; reachability: " + seed["last_check"]
    return pd.concat([reg, seed_rows], ignore_index=True)


def build_state_coverage(raw: list[dict], valid: list[dict]) -> pd.DataFrame:
    """Per-state *research coverage* table: how much we looked vs. what we found.
    Separates 'no evidence in our research' from 'no activity' (we can never claim the latter)."""
    hints = Counter(e.get("hint_state") for e in raw if e.get("hint_state"))
    by_state = defaultdict(list)
    for r in valid:
        by_state[r["state"]].append(r)
    rows = []
    for reg in REGIONS:
        rs = by_state.get(reg.name, [])
        pubs = {r["source_name"] for r in rs}
        n = len(rs)
        prim = sum(r["verification_status"] == "primary_source" for r in rs)
        corr = sum(r["verification_status"] == "corroborated" for r in rs)
        cats = sorted({r["category"] for r in rs})
        dates = sorted(r["published_date"] for r in rs if r["published_date"])
        if n == 0:
            status = "no_evidence_found_in_research"
        elif n < 3 or len(pubs) < 2:
            status = "limited_evidence"
        else:
            status = "documented_activity"
        rows.append({"state": reg.name, "state_code": reg.code, "state_type": reg.kind,
                     "raw_items_retrieved_for_state_queries": hints.get(reg.name, 0),
                     "records": n, "distinct_publishers": len(pubs), "primary_source_records": prim,
                     "corroborated_records": corr, "categories_covered": len(cats),
                     "category_list": "|".join(cats),
                     "institutions_named": len({i for r in rs for i in r["institutions"].split("|") if i}),
                     "first_record_date": dates[0] if dates else "", "last_record_date": dates[-1] if dates else "",
                     "evidence_status": status})
    return pd.DataFrame(rows).sort_values("records", ascending=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, nargs="+", help="raw snapshot(s) (default: all in data/raw)")
    ap.add_argument("--collect", action="store_true", help="run collection first")
    ap.add_argument("--check-seeds", action="store_true", help="probe reachability of seed official sites")
    ap.add_argument("--out", type=Path, default=PROCESSED)
    a = ap.parse_args(argv)
    cfg = load_config()
    if a.collect:
        collect(cfg, ROOT / "data" / "raw")
    raw = a.raw or all_raw(ROOT / "data" / "raw")
    summary = process(raw, a.out, window_days=cfg["window_days"], check_seeds=a.check_seeds)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
