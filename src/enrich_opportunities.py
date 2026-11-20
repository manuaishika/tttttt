"""Opportunity enrichment from publisher pages (network step, run on demand):

    python -m src.enrich_opportunities            # then: python -m src.pipeline

For each opportunity record it tries to read the ORIGINAL article and extract, with evidence:
application deadline, programme dates, eligibility, fees/stipend, mode/location, application URL
and organiser. Output: data/processed/opportunity_enrichment.csv (joined by the pipeline).

Source discovery, in order:
  1. direct publisher URLs on the record or on reports merged into it (duplicates.csv);
  2. exact-headline lookup in GNews/NewsAPI (keys optional; those APIs reach back ~30 days);
  Google News redirect tokens are NOT decoded.
Access rules: robots.txt must allow both generic agents ('*') and AI agents ('ClaudeBot',
'GPTBot'); a disallow is recorded as 'source_restricted', never as 'no deadline'.
Reviewer-supplied excerpts (config/opportunity_evidence.csv) are run through the SAME
extractor and labelled as reviewer-supplied.
"""
from __future__ import annotations
import csv, json, os, re, time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

import pandas as pd
import requests
from rapidfuzz import fuzz

from .opportunity_extract import (extract_application_urls, extract_deadlines, extract_eligibility,
                                  extract_fees_stipend, extract_mode_location, extract_organiser,
                                  extract_programme_dates)

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
UA = "ai-policy-tracker/0.1 (open research project; respects robots.txt)"
AI_AGENTS = ("ClaudeBot", "GPTBot")
_robots_cache: dict[str, robotparser.RobotFileParser | None] = {}


def robots_allows(url: str, sess: requests.Session) -> tuple[bool, str]:
    u = urlparse(url)
    base = f"{u.scheme}://{u.netloc}"
    if base not in _robots_cache:
        rp = robotparser.RobotFileParser()
        try:
            r = sess.get(base + "/robots.txt", timeout=15)
            if r.status_code >= 400:
                _robots_cache[base] = None            # no robots.txt: no stated restriction
            else:
                rp.parse(r.text.splitlines()); _robots_cache[base] = rp
        except requests.RequestException:
            _robots_cache[base] = None
    rp = _robots_cache[base]
    if rp is None:
        return True, "no robots.txt"
    for agent in ("*", *AI_AGENTS):
        if not rp.can_fetch(agent, url):
            return False, f"robots.txt disallows '{agent}'"
    return True, "allowed by robots.txt"


def article_text(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except ValueError:
            continue
        for d in (data if isinstance(data, list) else [data]):
            if isinstance(d, dict) and d.get("articleBody"):
                return str(d["articleBody"])
    node = soup.find("article") or soup.find("main") or soup
    return " ".join(p.get_text(" ", strip=True) for p in node.find_all("p"))


def api_lookup(title: str, published: str) -> list[str]:
    """Original URLs for an exact headline via the news APIs (only within their ~30-day window)."""
    try:
        if (date.today() - date.fromisoformat(published)).days > 29:
            return []
    except ValueError:
        return []
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    q = " ".join(title.split()[:10]).replace('"', "")
    urls = []
    try:
        if os.environ.get("NEWSAPI_KEY"):
            r = requests.get("https://newsapi.org/v2/everything", timeout=30,
                             params={"qInTitle": f'"{q}"', "language": "en", "pageSize": 5},
                             headers={"X-Api-Key": os.environ["NEWSAPI_KEY"]}).json()
            urls += [a["url"] for a in r.get("articles", []) if fuzz.token_set_ratio(a["title"], title) >= 90]
        if not urls and os.environ.get("GNEWS_API_KEY"):
            time.sleep(1.2)
            r = requests.get("https://gnews.io/api/v4/search", timeout=30,
                             params={"q": f'"{q}"', "in": "title", "lang": "en", "max": 5,
                                     "apikey": os.environ["GNEWS_API_KEY"]}).json()
            urls += [a["url"] for a in r.get("articles", []) if fuzz.token_set_ratio(a["title"], title) >= 90]
    except (requests.RequestException, ValueError, KeyError):
        pass
    return urls


def enrich(today: date | None = None) -> pd.DataFrame:
    today = today or datetime.now(timezone.utc).date()
    opps = pd.read_csv(PROC / "opportunities.csv", dtype=str, keep_default_na=False)
    dups = pd.read_csv(PROC / "duplicates.csv", dtype=str, keep_default_na=False)
    manual = {}
    mp = ROOT / "config" / "opportunity_evidence.csv"
    if mp.exists():
        for r in csv.DictReader(mp.open()):
            manual.setdefault(r["record_id"], []).append(r)
    sess = requests.Session(); sess.headers["User-Agent"] = UA
    rows = []
    for _, o in opps.iterrows():
        pub = date.fromisoformat(o["published_date"]) if o["published_date"] else None
        members = dups[dups["record_id"] == o["record_id"]]
        cands = [u for u in [o["source_url"], *members["source_url"].tolist()] if u and "news.google.com" not in u]
        via = "direct link on record/merged reports"
        if not cands:
            cands = api_lookup(o["title"], o["published_date"]); via = "exact-headline API lookup"
        cands = list(dict.fromkeys(cands))[:4]
        log, texts = [], []
        for u in cands:
            ok, why = robots_allows(u, sess)
            if not ok:
                log.append({"url": u, "status": "restricted", "detail": why}); continue
            try:
                r = sess.get(u, timeout=25)
                if r.status_code != 200:
                    log.append({"url": u, "status": "inaccessible", "detail": f"HTTP {r.status_code}"}); continue
                txt = article_text(r.text)
                if len(txt) < 200:
                    log.append({"url": u, "status": "inaccessible", "detail": "no article text found (paywall or script-rendered)"})
                    continue
                texts.append((u, txt, r.text, "publisher page")); log.append({"url": u, "status": "read", "detail": f"{len(txt)} chars"})
            except requests.RequestException as e:
                log.append({"url": u, "status": "inaccessible", "detail": type(e).__name__})
            time.sleep(1.0)
        for m in manual.get(o["record_id"], []):
            texts.append((m["source_url"], m["excerpt"], "", f"reviewer-supplied excerpt ({m['provided_by']}, {m['checked_on']})"))
            log.append({"url": m["source_url"], "status": "reviewer_excerpt", "detail": m["source_note"]})

        hits = [(u, kind, h) for u, txt, _, kind in texts for h in extract_deadlines(txt, pub)]
        dates = sorted({h.iso for _, _, h in hits})
        headline_dl = o.get("deadline", "")
        if headline_dl and dates and headline_dl not in dates:
            dates = sorted(set(dates) | {headline_dl})
        if len(dates) > 1:
            status, dl, conf = "conflict", "", ""
            ev = " || ".join(f"[{d}] {next((h.excerpt for _, _, h in hits if h.iso == d), 'headline')}" for d in dates)
            src = " | ".join(sorted({u for u, _, _ in hits}))
        elif hits:
            u, kind, h = max(hits, key=lambda x: {"high": 3, "medium": 2, "low": 1}[x[2].confidence])
            status, dl, conf, ev, src = "extracted", h.iso, h.confidence, f"{h.excerpt} [{kind}]", u
        elif texts:
            status, dl, conf, ev, src = "not_stated_in_accessible_sources", "", "", "", ""
        elif any(l["status"] == "restricted" for l in log):
            status, dl, conf, ev, src = "source_restricted", "", "", "", ""
        else:
            status, dl, conf, ev, src = "source_inaccessible", "", "", "", ""
        allt = " ".join(t for _, t, _, _ in texts)
        html = " ".join(h for _, _, h, _ in texts)
        host = urlparse(texts[0][0]).netloc if texts else ""
        notes = ("no publisher URL resolvable: Google News redirect not decoded; " + via + " found nothing"
                 if not cands and not texts else "")
        rows.append({
            "record_id": o["record_id"], "checked_on": today.isoformat(), "discovery": via if cands else "none",
            "sources_checked": json.dumps(log, ensure_ascii=False),
            "application_deadline": dl, "deadline_extraction_status": status, "deadline_confidence": conf,
            "deadline_evidence": ev, "deadline_source_url": src,
            "programme_dates": " || ".join(extract_programme_dates(allt)),
            "eligibility": " || ".join(extract_eligibility(allt)),
            "fees_stipend": " || ".join(extract_fees_stipend(allt)),
            "location_mode": " || ".join(extract_mode_location(allt)),
            "application_url": " | ".join(extract_application_urls(html, host)),
            "organiser": " || ".join(extract_organiser(allt)),
            "enrichment_notes": notes,
        })
    out = pd.DataFrame(rows)
    out.to_csv(PROC / "opportunity_enrichment.csv", index=False)
    return out


if __name__ == "__main__":
    e = enrich()
    print(e["deadline_extraction_status"].value_counts().to_string())
