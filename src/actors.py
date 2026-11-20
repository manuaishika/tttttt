"""Actor identification: WHO acted in a record, separated from WHERE and from the publisher.

Two layers:
  1. A curated registry (config/actor_registry.csv + the institution registry) of bodies whose
     identity and, where stated, statutory/administrative basis is established. Only these carry
     an `authority_note`; nothing is inferred for anyone else.
  2. Explicit headline cues for generic actors ("cabinet", "High Court", "police", "district
     collector"), classified by type and level only. Their legal authority is not asserted.

Identity (actor_class: e.g. regulator, judiciary) is kept apart from the record's action; when no
actor is identifiable from the headline the class is 'unknown', never guessed.
"""
from __future__ import annotations
import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .reference import INSTITUTIONS

ROOT = Path(__file__).resolve().parent.parent

ACTOR_CLASSES = {
    "union_ministry_department": "Union ministry / department",
    "union_government": "Union government (unspecified)",
    "state_government": "State / UT government",
    "local_government": "Local government",
    "policy_advisory_body": "Policy / advisory body",
    "regulator_statutory_authority": "Regulator / statutory authority",
    "legislature": "Legislature",
    "judiciary": "Judiciary",
    "public_research_institution": "Public research institution",
    "public_implementation_agency": "Public implementation agency / mission",
    "academic_research_institution": "University / research institute",
    "ai_lab_or_technology_company": "AI lab / technology company",
    "industry_association": "Industry association",
    "think_tank_civil_society": "Think tank / civil society",
    "international_organisation": "International organisation",
    "unknown": "Not identified",
}
LEVELS = {"union": "Union / national", "state": "State / UT", "local": "Local", "non_government": "Non-government",
          "international": "International", "unknown": "Unknown"}

# Institution-registry entries whose type differs from the generic 'academic' label.
_INSTITUTION_CLASS = {
    "TIFR Mumbai": ("public_research_institution", "union"),
    "C-DAC Pune": ("public_research_institution", "union"),
    "Wadhwani AI": ("think_tank_civil_society", "non_government"),
    "Telangana AI Mission (T-AIM)": ("public_implementation_agency", "state"),
    "Karnataka Digital Economy Mission (KDEM)": ("public_implementation_agency", "state"),
    "Kerala Startup Mission": ("public_implementation_agency", "state"),
}


@dataclass(frozen=True)
class Actor:
    name: str
    actor_class: str
    level: str
    authority_note: str = ""
    website: str = ""
    city: str = ""
    state: str = ""
    source: str = "registry"          # registry | institution_registry | headline_cue


def _pattern(alias: str) -> re.Pattern:
    body = r"[\s\-]+".join(re.escape(p) for p in re.split(r"[\s\-]+", alias) if p)
    flags = 0 if (alias.isupper() and len(alias) <= 6) else re.I   # acronyms (SC, BIS, ICMR) are case-sensitive
    return re.compile(r"(?<![\w])" + body + r"(?![\w])", flags)


@lru_cache(maxsize=1)
def registry() -> list[tuple[Actor, list[re.Pattern]]]:
    out = []
    sites = {}
    sp = ROOT / "config" / "stakeholder_websites.csv"
    if sp.exists():
        sites = {r["name"]: r["official_website"] for r in csv.DictReader(sp.open())}
    with (ROOT / "config" / "actor_registry.csv").open() as fh:
        for r in csv.DictReader(fh):
            aliases = [r["name"]] + [a for a in r["aliases"].split(";") if a]
            out.append((Actor(r["name"], r["actor_class"], r["level"], r["authority_note"], r["official_website"]),
                        [_pattern(a) for a in aliases]))
    for i in INSTITUTIONS:
        cls, lvl = _INSTITUTION_CLASS.get(i.name, ("academic_research_institution",
                                                   "state" if i.kind == "government" else "unknown"))
        out.append((Actor(i.name, cls, lvl, "", sites.get(i.name, ""), i.city, i.state, "institution_registry"),
                    [_pattern(a) for a in (i.name, *i.aliases)]))
    return out


# Generic cues: class + level only. Ordered by specificity.
_CUES: list[tuple[str, str, str, re.Pattern]] = [
    ("High Court", "judiciary", "state", re.compile(r"\b(high court|HC)\b", re.I)),
    ("State legislature", "legislature", "state", re.compile(r"\b(legislative assembly|assembly|MLAs?)\b", re.I)),
    ("Union government", "union_government", "union",
     # 'Centre' only in actor forms: never 'Centre of Excellence', 'AI Centre', 'data centre'.
     re.compile(r"(^Centre\b(?! of| for)|\bthe Centre\b(?! of| for)|\bCentre's\b|\bCentre (to|plans?|approves?|launch\w*|sets?|"
                r"announces?|asks?|notif\w+|seeks?|appoints?|says|moves?|issues?|proposes?|mulls?|forms?)\b|:\s*Centre\s*$|"
                r"(?i:\bCentral government\b|\bUnion (government|govt|cabinet|minister|ministry)\b|\bGovt of India\b|"
                r"\bGovernment of India\b))")),
    ("State government", "state_government", "state",
     re.compile(r"\b(cabinet|chief minister|CM|govt|government|minister|ministry|department|dept|secretariat|chief secretary|"
                r"governor|guv|state)\b", re.I)),
    ("State police", "state_government", "state", re.compile(r"\bpolice\b", re.I)),
    ("Local government", "local_government", "local",
     re.compile(r"\b(district (administration|collector)|collector|municipal\w*|corporation|panchayat|zilla parishad)\b", re.I)),
    ("University / institute", "academic_research_institution", "unknown",
     re.compile(r"\b(university|varsity|institute|college|IIT|IIIT|NIT|IIM|IISER)\b")),
]


def identify_actors(title: str, has_state: bool = True) -> list[Actor]:
    """Actors named in a headline: registry matches first, then generic cues for what remains.
    'State government' cues are only used when the record is anchored to a state."""
    found: list[Actor] = []
    names = set()
    for actor, pats in registry():
        if any(p.search(title) for p in pats):
            if actor.name not in names:
                found.append(actor); names.add(actor.name)
    classes = {a.actor_class for a in found}
    for name, cls, lvl, pat in _CUES:
        if cls in classes:
            continue
        if cls == "state_government" and (not has_state or "union_government" in classes):
            continue
        if cls == "academic_research_institution" and "academic_research_institution" in classes:
            continue
        if pat.search(title):
            found.append(Actor(name, cls, lvl, source="headline_cue")); classes.add(cls)
    return found


NATIONAL_CLASSES = {"union_ministry_department", "union_government", "policy_advisory_body",
                    "regulator_statutory_authority", "public_implementation_agency", "public_research_institution"}


def is_national_actor(actors: list[Actor]) -> bool:
    """A headline with no state anchor qualifies as a national-scope activity only if a Union
    body, national regulator, Parliament or the Supreme Court is the actor."""
    return any(a.level == "union" and (a.actor_class in NATIONAL_CLASSES or a.actor_class in ("legislature", "judiciary"))
               for a in actors)
