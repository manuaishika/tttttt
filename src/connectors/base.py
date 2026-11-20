"""Shared machinery for API connectors: credentials, query planning, quota/rate handling,
request logging and provenance.

Security: keys come only from environment variables (optionally loaded from a git-ignored
.env via python-dotenv). They are never written to raw files or logs: every error string
passes through `redact()` because request exceptions can echo the full URL.
"""
from __future__ import annotations
import csv, hashlib, json, os, time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

import requests

from ..reference import REGIONS

ROOT = Path(__file__).resolve().parents[2]
UA = "ai-policy-tracker/0.1 (open research project; news API discovery)"


def load_env() -> None:
    """Load .env from the project root if python-dotenv is installed; silently skip otherwise."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=False)
    except ImportError:
        pass


def redact(text: str, secrets: Iterable[str]) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "***")
    return text


class QuotaExhausted(Exception):
    """Daily/plan quota used up: stop this connector for this run (do not retry)."""


@dataclass
class ApiResponse:
    status: int
    articles: list[dict]
    total: int | None
    error: str = ""


@dataclass
class Connector:
    name: str                       # 'gnews' | 'newsapi'
    env_var: str
    min_interval: float             # seconds between requests (rate limit)
    fetch: Callable[["Connector", requests.Session, str, date, str], ApiResponse]
    to_entry: Callable[[dict], dict]   # API article -> partial raw entry

    @property
    def key(self) -> str | None:
        return os.environ.get(self.env_var) or None


def plan_queries(cfg: dict) -> list[dict]:
    """Priority-ordered plan: broad per region -> pan-India topics -> region x topic.
    Topic-major ordering in the last tier means every region gets its policy query before
    any region gets its second topic, so a partial budget still covers all 36 regions."""
    api = cfg["api"]
    plan = [{"query_id": f"{r.code}:broad", "query": api["state_broad_template"].format(s=r.name), "hint_state": r.name}
            for r in REGIONS]
    plan += [{"query_id": f"IN:{k}", "query": q, "hint_state": None} for k, q in api["pan_india_queries"].items()]
    for topic, tpl in api["state_topic_templates"].items():
        plan += [{"query_id": f"{r.code}:{topic}", "query": tpl.format(s=r.name), "hint_state": r.name} for r in REGIONS]
    return plan


def completed_query_ids(raw_dir: Path, api_name: str) -> set[str]:
    done = set()
    for log in raw_dir.glob(f"*/*_{api_name}_fetch_log.csv"):
        with log.open() as fh:
            for row in csv.DictReader(fh):
                if row["status"] == "200":
                    done.add(row["query_id"])
    return done


def run_connector(conn: Connector, cfg: dict, out_dir: Path, budget: int | None = None,
                  resume: bool = True, run_id: str | None = None) -> Path | None:
    key = conn.key
    if not key:
        print(f"[{conn.name}] skipped: {conn.env_var} not set")
        return None
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    day_dir = out_dir / f"{run_id[:4]}-{run_id[4:6]}-{run_id[6:8]}"
    day_dir.mkdir(parents=True, exist_ok=True)
    budget = budget if budget is not None else cfg["api"]["daily_budget"][conn.name]
    since = datetime.now(timezone.utc).date() - timedelta(days=cfg["api"]["window_days"])

    plan = plan_queries(cfg)
    if resume:
        done = completed_query_ids(out_dir, conn.name)
        plan = [q for q in plan if q["query_id"] not in done]
    plan = plan[:budget]

    sess = requests.Session()
    sess.headers["User-Agent"] = UA
    raw_path = day_dir / f"{run_id}_{conn.name}.jsonl"
    log_path = day_dir / f"{run_id}_{conn.name}_fetch_log.csv"
    n_entries, n_req, last = 0, 0, 0.0
    with raw_path.open("w") as fh, log_path.open("w", newline="") as lf:
        log = csv.writer(lf)
        log.writerow(["query_id", "api", "hint_state", "status", "error", "entries", "total_available", "fetched_at", "query"])
        for q in plan:
            wait = conn.min_interval - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
            last = time.monotonic()
            ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
            try:
                resp = conn.fetch(conn, sess, q["query"], since, key)
            except QuotaExhausted as e:
                log.writerow([q["query_id"], conn.name, q["hint_state"] or "", "quota", redact(str(e), [key]), 0, "", ts, q["query"]])
                print(f"[{conn.name}] quota exhausted after {n_req} requests: {redact(str(e), [key])}")
                break
            except requests.RequestException as e:
                resp = ApiResponse(0, [], None, redact(f"{type(e).__name__}: {e}", [key]))
            n_req += 1
            for i, art in enumerate(resp.articles):
                entry = conn.to_entry(art)
                if not entry.get("link") or not entry.get("title"):
                    continue   # missing metadata: nothing traceable to keep
                entry.update({
                    "query_id": q["query_id"], "query": q["query"], "hint_state": q["hint_state"],
                    "kind": "api", "api_source": conn.name, "feed_url": f"{conn.name}:search",
                    "fetched_at": ts, "url_type": "publisher_direct",
                    "raw_ref": f"{raw_path.name}#{hashlib.sha1(f'{q['query_id']}|{i}'.encode()).hexdigest()[:10]}",
                })
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
                n_entries += 1
            log.writerow([q["query_id"], conn.name, q["hint_state"] or "", resp.status, resp.error,
                          len(resp.articles), resp.total if resp.total is not None else "", ts, q["query"]])
    print(f"[{conn.name}] {n_req} requests, {n_entries} entries -> {raw_path}")
    return raw_path


def available_connectors() -> list[Connector]:
    load_env()
    from .gnews import CONNECTOR as G
    from .newsapi import CONNECTOR as N
    return [G, N]
