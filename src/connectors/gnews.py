"""GNews v4 /search connector.

Observed response (inspected 2026-11-20): {totalArticles, articles[], information?,
articlesRemovedFromResponse?}; article = {id, title, description, content (truncated),
url, image, publishedAt (ISO Z), lang, source{id, name, url, country}}.
Free plan: last 30 days, 12 h delay, max 10 articles/request, 1 request/second (HTTP 429
beyond that), daily request cap (HTTP 403 when reached). Full text is NOT available.
"""
from __future__ import annotations
import time
from datetime import date

import requests

from .base import ApiResponse, Connector, QuotaExhausted

URL = "https://gnews.io/api/v4/search"


def fetch(conn: Connector, sess: requests.Session, q: str, since: date, key: str) -> ApiResponse:
    params = {"q": q, "lang": "en", "country": "in", "max": 10, "sortby": "publishedAt",
              "from": f"{since.isoformat()}T00:00:00Z", "apikey": key}
    for attempt in range(3):
        r = sess.get(URL, params=params, timeout=30)
        if r.status_code == 429:                      # per-second rate limit: back off, retry
            time.sleep(1.5 * (attempt + 1)); continue
        break
    try:
        body = r.json()
    except ValueError:
        body = {}
    errors = " ".join(body.get("errors", [])) if isinstance(body.get("errors"), list) else str(body.get("errors", ""))
    if r.status_code == 403 or "request limit" in errors.lower() or "quota" in errors.lower():
        raise QuotaExhausted(f"HTTP {r.status_code}: {errors[:200]}")
    if r.status_code != 200:
        return ApiResponse(r.status_code, [], None, f"HTTP {r.status_code}: {errors[:200]}")
    note = "; ".join(v.get("message", "")[:80] for v in (body.get("articlesRemovedFromResponse") or {}).values())
    return ApiResponse(200, body.get("articles") or [], body.get("totalArticles"), note)


def to_entry(a: dict) -> dict:
    src = a.get("source") or {}
    return {"title": (a.get("title") or "").strip(), "link": a.get("url"), "published_raw": a.get("publishedAt"),
            "source_name": src.get("name"), "publisher_url": src.get("url"),
            "description": (a.get("description") or "").strip()}


CONNECTOR = Connector("gnews", "GNEWS_API_KEY", 1.2, fetch, to_entry)
