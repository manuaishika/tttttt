"""Collection: turn discovery queries and RSS feeds into an immutable raw snapshot.

Sources used (and why - see docs/rationale.md):
  * Google News RSS search  - broad, free, no API key, supports a date window; good for
    *discovery* across 36 regions. Limitations: items link to news.google.com redirects,
    carry only a headline (no snippet), ~100 items max per query.
  * Direct publisher / government RSS (PIB, MediaNama, ETGovernment, ...) - real article
    URLs and descriptions, but only recent items.

We never fetch article pages, never bypass paywalls and never resolve Google's redirect
tokens: the redirect link is kept as the source URL and the publisher identity (name +
home page, supplied by the feed itself) is kept alongside it.

Output: data/raw/<date>/<run_id>.jsonl (one raw entry per line) + fetch_log.csv.
Processing downstream reads only this snapshot, so a run is reproducible offline.
"""
from __future__ import annotations
import argparse, csv, json, time, random, hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import feedparser
import requests

from .reference import REGIONS

ROOT = Path(__file__).resolve().parent.parent
UA = "ai-policy-tracker/0.1 (open research project; RSS discovery)"


def load_config(path: Path | None = None) -> dict:
    return json.loads((path or ROOT / "config" / "discovery.json").read_text())


def build_queries(cfg: dict, regions: list[str] | None = None) -> list[dict]:
    """Expand templates into concrete queries. `hint_state` is only a *hint*; the state of
    a record is decided later from the text (a query for Kerala can return a Gujarat story)."""
    g = cfg["google_news"]
    days = cfg["window_days"]
    out = []

    def mk(qid, q, hint):
        params = {"q": f"{q} when:{days}d", **g["params"]}
        return {"query_id": qid, "query": q, "hint_state": hint, "kind": "google_news",
                "url": f"{g['base']}?{urlencode(params)}"}

    for r in REGIONS:
        if regions and r.name not in regions:
            continue
        for key, tpl in cfg["state_query_templates"].items():
            out.append(mk(f"{r.code}:{key}", tpl.format(s=r.name), r.name))
    if not regions:
        for key, q in cfg["pan_india_queries"].items():
            out.append(mk(f"IN:{key}", q, None))
    return out


def _fetch(session: requests.Session, url: str, retries: int = 3) -> tuple[int, bytes | None, str]:
    err = ""
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=25)
            if r.status_code == 200:
                return 200, r.content, ""
            err = f"HTTP {r.status_code}"
            if r.status_code in (400, 403, 404):
                break                       # not transient; do not hammer
        except requests.RequestException as e:
            err = type(e).__name__
        time.sleep(1.5 * (2 ** attempt) + random.random())
    return 0, None, err


def _entries(job: dict, content: bytes, fetched_at: str) -> list[dict]:
    feed = feedparser.parse(content)
    rows = []
    for e in feed.entries:
        src = e.get("source") or {}
        rows.append({
            "query_id": job["query_id"], "query": job["query"], "hint_state": job.get("hint_state"),
            "kind": job["kind"], "feed_url": job["url"], "fetched_at": fetched_at,
            "title": (e.get("title") or "").strip(),
            "link": e.get("link"),
            "published_raw": e.get("published") or e.get("updated"),
            "source_name": src.get("title") or job.get("source_name"),
            "publisher_url": src.get("href") or job.get("publisher_url"),
            "description": (e.get("summary") or "") if job["kind"] == "direct_feed" else "",
        })
    return rows


def collect(cfg: dict, out_dir: Path, regions: list[str] | None = None, workers: int = 4,
            include_direct: bool = True, limit_queries: int | None = None) -> Path:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    day_dir = out_dir / f"{run_id[:4]}-{run_id[4:6]}-{run_id[6:8]}"
    day_dir.mkdir(parents=True, exist_ok=True)

    jobs = build_queries(cfg, regions)
    if limit_queries:
        jobs = jobs[:limit_queries]
    if include_direct:
        for f in cfg["direct_feeds"]:
            jobs.append({"query_id": f"feed:{f['id']}", "query": f["name"], "hint_state": None,
                         "kind": "direct_feed", "url": f["url"], "source_name": f["name"],
                         "publisher_url": f.get("publisher_url")})

    sess = requests.Session()
    sess.headers["User-Agent"] = UA
    sess.headers["Accept"] = "application/rss+xml, application/xml;q=0.9, */*;q=0.5"

    def work(job):
        time.sleep(random.uniform(0.2, 0.8))      # politeness jitter
        status, content, err = _fetch(sess, job["url"])
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rows = _entries(job, content, ts) if content else []
        return job, status, err, rows, ts

    raw_path = day_dir / f"{run_id}.jsonl"
    log_path = day_dir / f"{run_id}_fetch_log.csv"
    n = 0
    with ThreadPoolExecutor(workers) as ex, raw_path.open("w") as fh, log_path.open("w", newline="") as lf:
        log = csv.writer(lf)
        log.writerow(["query_id", "kind", "hint_state", "status", "error", "entries", "fetched_at", "query"])
        for job, status, err, rows, ts in ex.map(work, jobs):
            for i, row in enumerate(rows):
                row["raw_ref"] = f"{raw_path.name}#{query_row_id(job['query_id'], i)}"
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += len(rows)
            log.writerow([job["query_id"], job["kind"], job.get("hint_state") or "", status, err, len(rows), ts, job["query"]])
    print(f"collected {n} raw entries from {len(jobs)} queries/feeds -> {raw_path}")
    return raw_path


def query_row_id(query_id: str, i: int) -> str:
    return hashlib.sha1(f"{query_id}|{i}".encode()).hexdigest()[:10]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Collect raw RSS entries into data/raw/")
    ap.add_argument("--regions", nargs="*", help="limit to these canonical state/UT names (default: all 36)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-direct", action="store_true", help="skip direct publisher/government feeds")
    ap.add_argument("--limit-queries", type=int)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "raw")
    a = ap.parse_args(argv)
    collect(load_config(), a.out, a.regions, a.workers, not a.no_direct, a.limit_queries)


if __name__ == "__main__":
    main()
