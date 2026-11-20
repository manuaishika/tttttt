"""Pure text extraction for opportunity details (no network). Every value is returned WITH the
exact excerpt that supports it, so nothing is asserted without evidence.

Deadline rule: a date counts as an application deadline only if it follows an explicit
deadline cue ("last date to apply/submit", "applications close", "apply by", "deadline",
"registration closes", "submit ... by") in the same sentence, with no programme/event cue
("starts", "commences", "begins", "held", "from ... to", "scheduled") between the cue and the
date. Dates without a cue (publication dates, programme dates) are never deadlines.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import date

from .normalize import normalize_date

_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DATE = (rf"(?:\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}\.?,?(?:\s+\d{{4}})?"
         rf"|{_MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?(?:\s+\d{{4}})?"
         rf"|\d{{1,2}}[/.\-]\d{{1,2}}[/.\-]\d{{4}})")
_DATE_RE = re.compile(_DATE, re.I)
STRONG_CUES = (r"last\s+date\s+(?:to|for)\s+(?:apply|submit|submission|register|registration|send|receipt)|"
               r"last\s+date\s+(?:of|for)\s+applications?|last\s+date\s+is|"
               r"applications?\s+(?:will\s+)?(?:close|closes|end|ends)|apply\s+(?:by|before|on\s+or\s+before)|"
               r"deadline|registrations?\s+(?:will\s+)?(?:close|closes|end|ends)|registration\s+deadline|"
               r"submit\w*\s+(?:\w+\s+){0,4}(?:by|before|on\s+or\s+before)|closing\s+date")
WEAK_CUES = r"(?:open|accepted|invited|registrations?|applications?)\s+(?:\w+\s+){0,3}(?:till|until|up\s+to)"
_CUE_RE = re.compile(rf"(?P<strong>{STRONG_CUES})|(?P<weak>{WEAK_CUES})", re.I)
_PROGRAMME_BETWEEN = re.compile(r"\b(start|starts|starting|commenc\w*|begin\w*|held|scheduled|from|conducted|runs?|"
                                r"inaugurat\w*|session|classes)\b", re.I)
_PROGRAMME_SENT = re.compile(r"\b(start\w*|commenc\w*|begin\w*|held\s+(?:on|from)|scheduled|will\s+be\s+conducted|"
                             r"from\s+.{0,40}\bto\b|duration|batch(?:es)?\s+(?:will\s+)?(?:run|start|begin))\b", re.I)


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "")
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“])", text) if s.strip()]


@dataclass
class DateHit:
    iso: str
    excerpt: str
    cue: str
    confidence: str          # high | medium | low


def _resolve(raw: str, ref: date | None) -> tuple[str | None, bool]:
    """Parse a matched date; a date without a year is resolved to its first occurrence on/after
    the reference (publication) date. Returns (iso, year_was_inferred)."""
    raw = re.sub(r"(\d)(st|nd|rd|th)", r"\1", raw.strip().rstrip(","))
    if re.search(r"\d{4}", raw):
        d = normalize_date(raw, allow_future=True)
        return (d.iso if d.precision == "day" else None), False
    if ref is None:
        return None, True
    for y in (ref.year, ref.year + 1):
        d = normalize_date(f"{raw} {y}", allow_future=True)
        if d.iso and date.fromisoformat(d.iso) >= ref:
            return d.iso, True
    return None, True


def extract_deadlines(text: str, ref: date | None = None) -> list[DateHit]:
    hits = []
    for s in sentences(text):
        for m in _CUE_RE.finditer(s):
            after = s[m.end(): m.end() + 90]
            dm = _DATE_RE.search(after)
            if not dm:
                continue
            between = after[:dm.start()]
            if _PROGRAMME_BETWEEN.search(between):
                continue          # "deadline ... the course starts on X": X is not the deadline
            weak = m.group("weak") is not None
            if weak and not re.search(r"\b(appl\w+|regist\w+|submi\w+|nominat\w+|entr(y|ies))\b", s, re.I):
                continue
            iso, inferred = _resolve(dm.group(0), ref)
            if not iso:
                continue
            conf = "low" if weak else ("medium" if inferred else "high")
            hits.append(DateHit(iso, s[:400], m.group(0), conf))
            break
    return hits


def extract_programme_dates(text: str) -> list[str]:
    """Sentences stating programme/event dates (start, duration, held on). Returned as evidence,
    never converted into a deadline."""
    return [s[:300] for s in sentences(text) if _PROGRAMME_SENT.search(s) and _DATE_RE.search(s)
            and not _CUE_RE.search(s)][:3]


def _first(text: str, pat: str, n: int = 2) -> list[str]:
    rx = re.compile(pat, re.I)
    return [s[:300] for s in sentences(text) if rx.search(s)][:n]


def extract_eligibility(text: str) -> list[str]:
    return _first(text, r"\b(eligib\w+|open\s+to|who\s+can\s+apply|candidates?\s+(?:must|should)|students?\s+(?:of|from|pursuing)|"
                        r"undergraduate|postgraduate|b\.?tech|m\.?tech|phd|minimum\s+qualification)\b")


def extract_fees_stipend(text: str) -> list[str]:
    return _first(text, r"\b(fees?|stipend|scholarship\s+amount|registration\s+fee|free\s+of\s+cost|no\s+fee|paid|"
                        r"(?:rs\.?|inr|₹)\s?[\d,]+)")


def extract_mode_location(text: str) -> list[str]:
    return _first(text, r"\b(online|offline|in[- ]person|hybrid|virtual|on[- ]campus|residential|remote|venue)\b")


def extract_application_urls(html: str, page_host: str) -> list[str]:
    """Links whose anchor text or URL indicates an application/registration page, excluding the
    article's own site navigation."""
    out = []
    for href, label in re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html or "", re.I | re.S):
        label_txt = re.sub(r"<[^>]+>", " ", label)
        if page_host and page_host in href:
            continue
        if re.search(r"facebook\.com|twitter\.com|//x\.com|whatsapp|linkedin\.com/(share|sharing)|t\.me/|telegram|"
                     r"pinterest|reddit\.com/submit|mailto:|share", href, re.I):
            continue          # social-share buttons are not application pages
        if re.search(r"apply|application|register|registration|portal|form|admission", label_txt + " " + href, re.I):
            out.append(href)
    return list(dict.fromkeys(out))[:3]


def extract_organiser(text: str) -> list[str]:
    return _first(text, r"\b(organi[sz]ed\s+by|conducted\s+by|offered\s+by|hosted\s+by|in\s+collaboration\s+with|"
                        r"under\s+the\s+aegis\s+of)\b", 1)
