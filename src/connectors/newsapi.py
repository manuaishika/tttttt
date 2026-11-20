"""NewsAPI /v2/everything connector.

Observed response (inspected 2026-11-20): {status, totalResults, articles[]}; article =
{source{id, name}, author, title, description, url, urlToImage, publishedAt (ISO Z),
content (truncated with '…')}. Errors: {status:'error', code, message}; e.g. 426
'parameterInvalid' for dates beyond the plan's ~1-month history, 401 'apiKeyInvalid',
429 'rateLimited' when the daily cap is hit. No publisher home page is returned, so it is
derived from the article URL's host. Full text is NOT available.
"""
from __future__ import annotations
from datetime import date
from urllib.parse import urlparse

import requests

from .base import ApiResponse, Connector, QuotaExhausted

URL = "https://newsapi.org/v2/everything"


def fetch(conn: Connector, sess: requests.Session, q: str, since: date, key: str) -> ApiResponse:
    params = {"q": q, "language": "en", "pageSize": 100, "sortBy": "publishedAt", "from": since.isoformat()}
    r = sess.get(URL, params=params, headers={"X-Api-Key": key}, timeout=30)
    try:
        body = r.json()
    except ValueError:
        body = {}
    if body.get("status") == "ok":
        return ApiResponse(200, body.get("articles") or [], body.get("totalResults"))
    code, msg = body.get("code", ""), body.get("message", "")
    if r.status_code == 429 or code in ("rateLimited", "apiKeyExhausted", "apiKeyDisabled"):
        raise QuotaExhausted(f"HTTP {r.status_code} {code}: {msg[:200]}")
    return ApiResponse(r.status_code, [], None, f"HTTP {r.status_code} {code}: {msg[:200]}")


def to_entry(a: dict) -> dict:
    url = a.get("url")
    if not url or "removed.com" in url:          # NewsAPI placeholder for withdrawn articles
        return {}
    u = urlparse(url)
    return {"title": (a.get("title") or "").strip(), "link": url, "published_raw": a.get("publishedAt"),
            "source_name": (a.get("source") or {}).get("name"), "publisher_url": f"{u.scheme}://{u.netloc}",
            "description": (a.get("description") or "").strip()}


CONNECTOR = Connector("newsapi", "NEWSAPI_KEY", 0.3, fetch, to_entry)
