"""Cross-outlet duplicate detection.

Problem: one announcement is reported by many outlets, each with a slightly different
headline ("Kerala cabinet approves AI mission - The Hindu" / "AI Mission gets Kerala
cabinet nod | NDTV"). We collapse them into ONE record and keep the evidence.

Method (all thresholds are parameters and documented in docs/methodology.md):
  1. Normalise headlines: strip publisher suffix, lowercase, expand common abbreviations,
     drop stopwords/punctuation.
  2. Block by state (a cheap way to avoid O(n^2) and to avoid merging two states' stories).
  3. Within a block, link pairs whose rapidfuzz token_set_ratio >= `threshold`, whose
     publication dates are within `window_days`, and (for non-identical titles) that share
     at least `min_shared_tokens` meaningful tokens - this protects against short generic
     headlines matching by accident.
  4. Connected components (union-find) form clusters; exact-URL repeats always merge.
  5. The canonical record is the one from the most authoritative source tier, then the
     earliest publication date. Everything else is kept in duplicates.csv for audit.
"""
from __future__ import annotations
import re
from datetime import date
from rapidfuzz import fuzz

from .sources import TIER

_STOP = set("a an the of in on for to and or with by at from as is are be will has have into over after amid says say said new".split())
_ABBR = {"govt": "government", "govts": "governments", "cm": "chief minister", "hc": "high court",
         "artificial intelligence": "ai", "keralam": "kerala", "mou": "mou", "centre": "center"}


def normalize_title(title: str, publisher: str | None = None) -> str:
    t = title or ""
    if publisher:  # strip " - Publisher" / " | Publisher" suffixes
        t = re.sub(r"\s*[-|–—:]\s*" + re.escape(publisher) + r"\s*$", "", t, flags=re.I)
    t = t.casefold()
    for k, v in _ABBR.items():
        t = re.sub(r"\b" + re.escape(k) + r"\b", v, t)
    t = re.sub(r"[^a-z0-9₹ ]+", " ", t)
    toks = [w for w in t.split() if w not in _STOP]
    return " ".join(toks)


class _UF:
    def __init__(self, n): self.p = list(range(n))
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[max(ra, rb)] = min(ra, rb)


def _days(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def cluster(items: list[dict], threshold: int = 82, window_days: int = 21, min_shared_tokens: int = 3) -> list[int]:
    """Return a cluster index per item. Items need: state, norm_title, published_date, url."""
    n = len(items)
    uf = _UF(n)
    by_state: dict[str, list[int]] = {}
    by_url: dict[str, int] = {}
    for i, it in enumerate(items):
        by_state.setdefault(it["state"], []).append(i)
        u = it.get("url")
        if u:
            if u in by_url: uf.union(i, by_url[u])
            else: by_url[u] = i
    for idxs in by_state.values():
        for a_pos, i in enumerate(idxs):
            ti = items[i]["norm_title"]
            toks_i = set(ti.split())
            for j in idxs[a_pos + 1:]:
                if uf.find(i) == uf.find(j):
                    continue
                gap = _days(items[i]["published_date"], items[j]["published_date"])
                if gap is not None and gap > window_days:
                    continue
                tj = items[j]["norm_title"]
                if ti == tj:
                    uf.union(i, j); continue
                if len(toks_i & set(tj.split())) < min_shared_tokens:
                    continue
                if fuzz.token_set_ratio(ti, tj) >= threshold and fuzz.token_sort_ratio(ti, tj) >= threshold - 17:
                    uf.union(i, j)
    return [uf.find(i) for i in range(n)]


def pick_canonical(members: list[dict]) -> dict:
    """Most authoritative tier, then a direct publisher URL over a Google News redirect, then
    one with a publisher description, then earliest date (ISO strings sort correctly)."""
    return sorted(members, key=lambda m: (TIER.get(m["source_type"], 9),
                                          0 if m.get("url_type", "publisher_direct") == "publisher_direct" else 1,
                                          0 if m.get("has_description") else 1,
                                          m["published_date"] or "9999"))[0]


_TRACKING = re.compile(r"^(utm_\w+|fbclid|gclid|ref|ref_src|cmpid|from|ito|mc_\w+|guccounter)$", re.I)


def canonical_url(url: str) -> str:
    """Comparable form of a URL for exact-duplicate detection across RSS and APIs: lower-case
    host without www/m./amp., no tracking params, no fragment, no trailing slash, http==https."""
    from urllib.parse import urlsplit, parse_qsl, urlencode
    if not url:
        return ""
    u = urlsplit(url.strip())
    host = u.netloc.lower()
    for pre in ("www.", "m.", "amp."):
        if host.startswith(pre):
            host = host[len(pre):]
    path = re.sub(r"/amp/?$|/amp(?=/)", "", u.path).rstrip("/")
    q = urlencode(sorted((k, v) for k, v in parse_qsl(u.query) if not _TRACKING.match(k)))
    return f"{host}{path}" + (f"?{q}" if q else "")
