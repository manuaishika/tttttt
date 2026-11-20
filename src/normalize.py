"""Normalisation of states, cities, institutions and dates.

Two entry styles:
  * structured input  -> `normalize_state("UP")`, `normalize_date("March 2025")`
  * free text         -> `extract_states(title + summary)`, `extract_institutions(...)`

Design choice: abbreviations (UP, MP, AP...) are accepted ONLY for whole-field structured
input. In free text they are too ambiguous (MP = Member of Parliament, AP = Associated
Press), so text extraction uses full names, aliases and cities only.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime

from rapidfuzz import fuzz, process

from .reference import (REGIONS, REGION_BY_NAME, CITY_TO_STATE, CITY_ALIAS, CITY_COORDS,
                        INSTITUTIONS, Institution)

# ---------------------------------------------------------------- states ---

def _key(s: str) -> str:
    """Canonical lookup key: casefold, '&'->'and', collapse punctuation/hyphens/spaces."""
    s = s.casefold().replace("&", " and ")
    s = re.sub(r"\b(government|govt|state|govt\.)\s+of\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"\s(?:state|government|govt)$", "", s)   # "Maharashtra State" -> "maharashtra"


_EXACT: dict[str, str] = {}
for _r in REGIONS:
    _EXACT[_key(_r.name)] = _r.name
    _EXACT[_key(_r.name).replace(" ", "")] = _r.name          # "uttarpradesh", "tamilnadu"
    for _a in _r.aliases:
        _EXACT[_key(_a)] = _r.name
        _EXACT[_key(_a).replace(" ", "")] = _r.name
    for _c in _r.codes:
        _EXACT.setdefault(_key(_c), _r.name)                    # codes: whole-field only
_EXACT["new delhi"] = "Delhi"  # in a *structured state field* "New Delhi" means the UT
_NAME_KEYS = [k for k in _EXACT if " " in k or len(k) > 4]


@dataclass(frozen=True)
class StateMatch:
    state: str
    method: str          # exact | alias | code | fuzzy
    evidence: str        # the raw text that was matched


def normalize_state(raw: str | None, fuzzy_threshold: int = 85) -> StateMatch | None:
    """Map a raw state field to a canonical state/UT name. Returns None if unmatched.

    >>> normalize_state("UP").state
    'Uttar Pradesh'
    >>> normalize_state("Uttar-Pradesh").state
    'Uttar Pradesh'
    """
    if not raw or not str(raw).strip():
        return None
    k = _key(str(raw))
    if k in _EXACT:
        name = _EXACT[k]
        region = REGION_BY_NAME[name]
        if k == _key(name) or k == _key(name).replace(" ", ""):
            method = "exact"
        elif any(k == _key(a) or k == _key(a).replace(" ", "") for a in region.aliases):
            method = "alias"
        else:
            method = "code"
        return StateMatch(name, method, str(raw))
    # typo tolerance — only against full names/aliases, with a high bar, and never for
    # very short strings (to avoid "Bihar" ~ "Bihari" style accidents).
    if len(k) >= 6:
        hit = process.extractOne(k, _NAME_KEYS, scorer=fuzz.ratio, score_cutoff=fuzzy_threshold)
        if hit:
            return StateMatch(_EXACT[hit[0]], "fuzzy", str(raw))
    return None


# Free-text patterns: names + aliases (word-bounded, hyphen/space tolerant).
def _name_pattern(name: str) -> str:
    parts = [re.escape(p) for p in re.split(r"[\s\-]+", name.replace("&", "and")) if p]
    body = r"[\s\-]+".join(parts)
    body = body.replace("and", "(?:and|&)") if "and" in name.split() else body
    return body


_TEXT_PATTERNS: list[tuple[str, re.Pattern]] = []
for _r in REGIONS:
    names = [_r.name, *_r.aliases]
    pats = []
    for n in names:
        if n in ("Delhi",):
            continue  # handled specially below
        p = _name_pattern(n)
        pats.append(p)
    if _r.name == "Jammu and Kashmir":
        pats.append(r"J\s?&\s?K\b")
    if pats:
        _TEXT_PATTERNS.append((_r.name, re.compile(r"(?<![\w])(?:" + "|".join(pats) + r")(?![\w])", re.I)))

# "Delhi" needs care: "New Delhi" is the centre-of-government dateline in almost every
# national story, so a bare "New Delhi" is NOT evidence of a Delhi-state activity.
_DELHI = re.compile(r"(?<!New )(?<![\w])(?:NCT of Delhi|Delhi\s+(?:govt|government|cabinet|CM|chief minister|university|police)|"
                    r"(?:Government|Govt) of (?:NCT of )?Delhi|(?<!New )Delhi(?![\w]))", re.I)


def extract_states(text: str) -> list[tuple[str, str]]:
    """Return [(canonical_state, evidence_snippet)] in order of first appearance."""
    if not text:
        return []
    found: dict[str, tuple[int, str]] = {}
    for name, pat in _TEXT_PATTERNS:
        m = pat.search(text)
        if m:
            found[name] = (m.start(), m.group(0))
    m = _DELHI.search(text)
    if m:
        found.setdefault("Delhi", (m.start(), m.group(0)))
    for name, pat in _ABBR_CTX:
        m = pat.search(text)
        if m and name not in found:
            found[name] = (m.start(), m.group(0).strip())
    return [(n, ev) for n, (pos, ev) in sorted(found.items(), key=lambda kv: kv[1][0])]


# Contextual abbreviations: a bare "MP"/"UP"/"AP" is ambiguous (Member of Parliament, "up",
# Associated Press) so it is only accepted in forms that are unambiguous in Indian news:
# "MP govt", "in UP", "A.P.", a leading "TN ...". Case-sensitive on purpose.
_GOVT = r"(?:govt|government|cabinet|CM|chief minister|police|assembly|minister)"
_ABBR_CTX: list[tuple[str, re.Pattern]] = [
    ("Madhya Pradesh", re.compile(rf"\bMP\s+{_GOVT}\b|\b(?:in|across)\s+MP\b|\bM\.P\.")),
    ("Uttar Pradesh", re.compile(rf"\bUP\s+{_GOVT}\b|\b(?:in|across|of)\s+UP\b|\bU\.P\.|^UP\b")),
    ("Andhra Pradesh", re.compile(rf"\bAP\s+{_GOVT}\b|\b(?:in|across)\s+AP\b|\bA\.P\.")),
    ("Tamil Nadu", re.compile(rf"\bTN\s+{_GOVT}\b|\b(?:in|across)\s+TN\b|^TN\b")),
    ("West Bengal", re.compile(rf"\bWB\s+{_GOVT}\b|\b(?:in|across)\s+WB\b")),
    ("Maharashtra", re.compile(rf"\bMaha\s+{_GOVT}\b")),
]

_CITY_PATTERNS = [(c, re.compile(r"(?<![\w])" + re.escape(c) + r"(?![\w])")) for c in CITY_TO_STATE]


def extract_cities(text: str) -> list[tuple[str, str]]:
    """Return [(canonical_city, state)] for cities mentioned (case-sensitive: proper nouns)."""
    out, seen = [], set()
    for c, pat in _CITY_PATTERNS:
        if pat.search(text or ""):
            canon = CITY_ALIAS.get(c, c)
            if canon not in seen:
                seen.add(canon)
                out.append((canon, CITY_TO_STATE[c]))
    return out


def city_coords(city: str) -> tuple[float, float] | None:
    return CITY_COORDS.get(CITY_ALIAS.get(city, city))


def _inst_pattern(alias: str) -> str:
    parts = [re.escape(p) for p in re.split(r"[\s\-]+", alias) if p]
    return r"[\s\-]+".join(parts)


_INST_PATTERNS: list[tuple[Institution, re.Pattern]] = []
for _i in INSTITUTIONS:
    pats = [_inst_pattern(a) for a in (_i.name, *_i.aliases)]
    # Short all-caps acronyms (IISc, IITM, KDEM) must match case-sensitively.
    _INST_PATTERNS.append((_i, re.compile(r"(?<![\w])(?:" + "|".join(pats) + r")(?![\w])")))
_INST_PATTERNS_CI = [(i, re.compile(r"(?<![\w])(?:" + "|".join(_inst_pattern(a) for a in (i.name, *i.aliases)) + r")(?![\w])", re.I))
                     for i in INSTITUTIONS]


def mask_institutions(text: str) -> str:
    """Blank out registry institution names so that 'Delhi' in 'IIT Delhi' or 'Kerala' in 'Digital
    University Kerala' is not read as the place where an activity happens. The institution still
    counts as evidence, but as the ACTOR's location (location_basis = actor_location_institution)."""
    for (inst, cs), (_, ci) in zip(_INST_PATTERNS, _INST_PATTERNS_CI):
        text = (ci if " " in inst.name else cs).sub(" ", text)
    return text


def extract_institutions(text: str) -> list[Institution]:
    """Institutions from the seed registry mentioned in `text`.

    Case-insensitive for names with 2+ words, case-sensitive otherwise so that the
    acronym 'IISc' matches but a stray lowercase word does not.
    """
    out = []
    for (inst, cs), (_, ci) in zip(_INST_PATTERNS, _INST_PATTERNS_CI):
        if ci.search(text or "") if " " in inst.name else cs.search(text or ""):
            out.append(inst)
        elif cs.search(text or ""):
            out.append(inst)
    # preserve registry order, dedupe
    seen, uniq = set(), []
    for i in out:
        if i.name not in seen:
            seen.add(i.name); uniq.append(i)
    return uniq


# ----------------------------------------------------------------- dates ---

@dataclass(frozen=True)
class DateResult:
    iso: str | None      # ISO date (start of period for month/year precision) or None
    precision: str       # day | month | year | unknown
    note: str            # how it was parsed / why unknown


_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}
_MONTHS.update({k[:3]: v for k, v in list(_MONTHS.items())})
_MONTHS["sept"] = 9
_APPROX = re.compile(r"\b(circa|around|about|approx\w*|early|late|mid|end of|beginning of|"
                     r"q[1-4]|h[12]|first half|second half|spring|summer|autumn|winter)\b", re.I)


def normalize_date(raw: str | date | datetime | None, today: date | None = None,
                   allow_future: bool = False) -> DateResult:
    """Parse a date and say how precise it is. Never invents a date.

    * Full dates (ISO, RFC-822 feed dates, '5 March 2025', 'March 5, 2025') -> precision 'day'
    * 'March 2025' -> '2025-03-01', precision 'month'
    * '2025' -> '2025-01-01', precision 'year'
    * approximate wording ('early 2025', 'Q3 2025') or garbage -> None, 'unknown', with a note
    * dates in the future relative to `today` are rejected (feeds sometimes carry bad dates)
      unless `allow_future=True` (used for application deadlines, which are future by nature)
    """
    today = today or datetime.now(timezone.utc).date()
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return DateResult(None, "unknown", "missing")
    if isinstance(raw, datetime):
        d = raw.date(); res = DateResult(d.isoformat(), "day", "datetime object")
    elif isinstance(raw, date):
        res = DateResult(raw.isoformat(), "day", "date object")
    else:
        s = str(raw).strip()
        res = _parse_str(s)
    if res.iso and not allow_future and date.fromisoformat(res.iso) > today:
        return DateResult(None, "unknown", f"rejected: {res.iso} is in the future")
    return res


def _parse_str(s: str) -> DateResult:
    if _APPROX.search(s):
        return DateResult(None, "unknown", f"approximate/ambiguous wording: {s!r}")
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?", s)
    if m:
        return _safe_ymd(int(m[1]), int(m[2]), int(m[3]), "day", "ISO")
    m = re.fullmatch(r"(\d{4})-(\d{2})", s)
    if m:
        return _safe_ymd(int(m[1]), int(m[2]), 1, "month", "ISO year-month")
    if re.fullmatch(r"\d{4}", s):
        return _safe_ymd(int(s), 1, 1, "year", "year only")
    # RFC-822 style from RSS: 'Tue, 22 Sep 2026 07:00:00 GMT'
    if re.match(r"^[A-Za-z]{3},\s", s):
        try:
            return DateResult(parsedate_to_datetime(s).date().isoformat(), "day", "RFC-822 feed date")
        except (TypeError, ValueError):
            pass
    # '5 March 2025' / '5th Mar 2025'
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?[\s\-/]+([A-Za-z]{3,9})\.?,?[\s\-/]+(\d{4})", s)
    if m and m[2].lower() in _MONTHS:
        return _safe_ymd(int(m[3]), _MONTHS[m[2].lower()], int(m[1]), "day", "D Month YYYY")
    # 'March 5, 2025'
    m = re.fullmatch(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", s)
    if m and m[1].lower() in _MONTHS:
        return _safe_ymd(int(m[3]), _MONTHS[m[1].lower()], int(m[2]), "day", "Month D, YYYY")
    # 'March 2025'
    m = re.fullmatch(r"([A-Za-z]{3,9})\.?,?\s+(\d{4})", s)
    if m and m[1].lower() in _MONTHS:
        return _safe_ymd(int(m[2]), _MONTHS[m[1].lower()], 1, "month", "Month YYYY")
    # DD/MM/YYYY or DD-MM-YYYY — Indian convention is day-first
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s)
    if m:
        return _safe_ymd(int(m[3]), int(m[2]), int(m[1]), "day", "DD/MM/YYYY (day-first assumed)")
    return DateResult(None, "unknown", f"unparseable: {s!r}")


def _safe_ymd(y: int, mo: int, d: int, precision: str, note: str) -> DateResult:
    try:
        return DateResult(date(y, mo, d).isoformat(), precision, note)
    except ValueError:
        return DateResult(None, "unknown", f"invalid calendar date {y}-{mo}-{d}")
