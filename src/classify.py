"""Rule-based classification and the inclusion/exclusion screen (v1: keywords).

Deliberately transparent: every category is a short list of (regex, weight) rules and the
rules that fired are returned with the result, so any label can be explained in an
interview or audit. The module boundary (`classify(text) -> Classification`) is where a
semantic/embedding classifier can later replace or be blended with these rules.

INCLUSION CRITERIA (all must hold)  -> "how we drew the line"
  1. AI-related: the headline/description is about artificial intelligence (not Air India).
  2. State anchor: a state/UT is identifiable from the text, an institution or a city.
  3. Public actor: a government body, public institution, court, police, mission or
     research institution is involved (company-only news is out of scope).
  4. Activity cue: at least one taxonomy rule fires (an announcement, deployment,
     partnership, research launch, safety/ethics move, or opportunity).
EXCLUSIONS (each has a reason code): not_ai_related, opinion_or_commentary,
  crime_or_scam_story, market_or_product_news, no_public_actor, no_category_match,
  state_not_in_text (query hint only), no_state_anchor.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

from . import schema as S
from .normalize import normalize_date

_I = re.I

# ------------------------------------------------------------ AI relevance ---
_AI_TERMS = re.compile(
    r"(?<![\w])(AI|A\.I\.|GenAI|Gen[- ]AI|LLMs?|AGI)(?![\w])"      # case-sensitive acronyms
    r"|artificial[- ]intelligence|machine[- ]learning|generative|deep[- ]?learning|"
    r"large language model|neural network|\bchatbots?\b|deepfakes?|\bAI[- ](?:powered|based|enabled|driven)\b", _I)
_AI_ACRONYM = re.compile(r"(?<![\w])(AI|A\.I\.|GenAI|LLMs?|AGI)(?![\w])")        # strictly upper-case
_AIR_INDIA = re.compile(r"Air[- ]India|\bAI[- ]?\d{3,4}\b|Air India Express|AI Express", _I)


def is_ai_related(text: str) -> bool:
    t = _AIR_INDIA.sub(" ", text)          # 'Air India' / flight numbers are not AI
    if _AI_ACRONYM.search(t):
        return True
    return bool(re.search(
        r"artificial[- ]intelligence|machine[- ]learning|generative|deep[- ]?learning|large language model|"
        r"neural network|\bchatbots?\b|deepfakes?", t, _I))


# ----------------------------------------------------------- category rules ---
# (pattern, weight). Patterns run on the casefolded "title. description".
CATEGORY_RULES: dict[str, list[tuple[str, float]]] = {
    "policy_governance": [
        (r"\bai (policy|mission|strategy|framework|roadmap|vision|governance|task ?force|council|regulation|law|act|bill)\b", 3),
        (r"(policy|mission|task ?force|committee|framework|guidelines?|roadmap|council|regulation|law)\s+(on|for|to govern)\s+(ai|artificial intelligence)", 3),
        (r"\b(ai|artificial intelligence)\b.{0,25}\b(mission|policy|task ?force)\b", 2),
        (r"\b(cabinet|state government|govt|government|assembly|ministry|department)\b.{0,50}\b(approves?|notif\w+|unveils?|launch\w*|constitutes?|announces?|releases?|adopts?)\b.{0,60}\b(ai|artificial intelligence)\b", 2),
        (r"\b(ai|artificial intelligence)\b.{0,60}\b(approved|notified|unveiled|launched|constituted|released|adopted)\b", 1),
        (r"\bai (usage|use) policy|\bpolicy (barring|banning|restricting|on use of) ai\b", 3),
        (r"\bai (state|nodal) (agency|cell|unit|directorate)|\bai (office|directorate)\b|\bchief ai officer\b", 2),
    ],
    "deployment": [
        (r"\b(use[sd]?|using|deploy\w*|rolls? out|rolled out|pilot\w*|introduc\w+|adopt\w*|implement\w*)\b.{0,60}\b(ai|artificial intelligence)\b", 2),
        (r"\b(ai|artificial intelligence)\b.{0,50}\b(crop|farmer|agricultur\w+|hospital|health\w*|tb\b|cancer|screening|police|policing|traffic|classroom|school|e-?governance|citizen|flood|forecast\w*|disaster|surveillance|smart city|chatbot|grievance|land record|welfare|courts?)\b", 2),
        (r"\bai[- ](powered|based|enabled|driven)\b", 1.5),
        (r"\bai (chatbot|assistant|tool|platform|system|app|cameras?|kiosks?|helpline)\b", 1.5),
    ],
    "research_institutions": [
        (r"\b(centre|center) of excellence\b|\bcoe\b", 3),
        (r"\bai (lab|laborator\w+|research (centre|center|hub|park)|institute|university|city|hub|campus|park|valley)\b", 3),
        (r"\b(supercomputer|data ?cent(er|re)s?|gpu|compute (cluster|capacity|infrastructure))\b", 2),
        (r"\b(iit|iisc|iiser|iiit|university|institute)\b.{0,60}\b(ai|artificial intelligence)\b", 1.5),
        (r"\b(ai|artificial intelligence)\b.{0,60}\b(research|laborator\w+|centre|center|department|school|programme|program|course)\b", 1),
    ],
    "partnerships_investment": [
        (r"\b(mou|mous|memorandum of understanding|tie[- ]?up|pact|inks|signs? (an? )?(agreement|deal))\b", 3.5),
        (r"\b(partner\w*|collaborat\w+|alliance)\b.{0,50}\b(ai|artificial intelligence)\b|\b(ai|artificial intelligence)\b.{0,50}\b(partner\w*|collaborat\w+)\b", 2),
        (r"\b(invest\w*|funding|crore|lakh crore|budget|allocat\w+|outlay|grant|sanction\w*|earmark\w*)\b", 2),
    ],
    "safety_responsible_ai": [
        (r"\bresponsible ai\b|\bai (ethics|safety|alignment|accountability|fairness|risk|audit\w*|bias|assurance|oversight)\b|\b(ethical|trustworthy|safe) ai\b", 3),
        (r"\balgorithmic (bias|accountability|audit\w*|fairness)\b", 3),
        (r"\bdeepfakes?\b.{0,40}\b(rules?|regulat\w+|law|ban|guidelines?|framework|advisory|labell?ing)\b", 2.5),
        (r"\b(ethics|ethical)\b.{0,30}\b(ai|artificial intelligence)\b|\b(ai|artificial intelligence)\b.{0,30}\b(ethics|ethical|privacy|transparen\w+)\b", 2),
    ],
    "education_opportunities": [
        (r"\b(fellowship|internship|scholarship|bootcamp|summer school|hackathon|workshop)s?\b", 3),
        (r"\b(curriculum|syllabus|skilling|upskill\w*|reskill\w*|ai literacy|training programme|training program|certificate course)\b", 2),
        (r"\b(teach\w*|learn\w*|students?|schools?|colleges?)\b.{0,40}\b(ai|artificial intelligence)\b|\b(ai|artificial intelligence)\b.{0,40}\b(students?|schools?|colleges?|curriculum|course)\b", 2),
        (r"\b(conference|summit|seminar|symposium)\b", 1.5),
    ],
}
_COMPILED = {c: [(re.compile(p, _I), w) for p, w in rules] for c, rules in CATEGORY_RULES.items()}
TIE_PRECEDENCE = ["safety_responsible_ai", "policy_governance", "partnerships_investment",
                  "research_institutions", "deployment", "education_opportunities"]

SECTOR_RULES = {
    "agriculture": r"\b(agri\w*|farm\w*|crops?|kisan|irrigation|soil|horticulture|fisher\w+|dairy|livestock)\b",
    "healthcare": r"\b(health\w*|hospitals?|medical|medicine|tb\b|tuberculosis|cancer|diseases?|patients?|diagnos\w+|telemedicine|aiims|doctors?|clinic\w*)\b",
    "defence": r"\b(defen[cs]e|army|military|navy|air force|drdo|border|armed forces|paramilitary|security forces)\b",
    "policing_justice": r"\b(police|policing|crime|cops?|judiciary|judges?|high court|supreme court|courts?|law enforcement|cctv|forensic\w*)\b",
    "education": r"\b(schools?|students?|classrooms?|curricul\w+|teachers?|literacy|exams?|learners?)\b",
    "environment": r"\b(climate|environment\w*|forests?|pollution|air quality|flood\w*|disaster|wildlife|monsoon|weather|water (management|resources)|biodiversity)\b",
    "infrastructure": r"\b(traffic|transport\w*|metro|roads?|railways?|smart cit\w+|infrastructure|power grid|energy|urban|municipal\w*|airport|ports?|logistics|mobility)\b",
    "public_administration": r"\b(governance|e-?governance|citizens?|grievance|administration|secretariat|public services?|welfare|land records?|revenue|panchayat|civil services?|bureaucra\w+|government services|helpline)\b",
}
_SECTOR_C = {k: re.compile(v, _I) for k, v in SECTOR_RULES.items()}

# ------------------------------------------------------------- opportunities ---
_OPP_TYPE = [
    ("fellowship", r"\bfellowships?\b"), ("internship", r"\binternships?\b"),
    ("scholarship", r"\bscholarships?\b"), ("competition", r"\b(hackathon|competition|challenge|contest)s?\b"),
    ("research_programme", r"\b(summer school|research programme|research program|bootcamp|training programme|certificate course|residency)\b"),
    ("workshop", r"\bworkshops?\b"), ("conference", r"\b(conference|summit|symposium|seminar)s?\b"),
]
_OPP_FORWARD = re.compile(
    r"\b(applications?\s+(are\s+)?(open|invited)|apply\s+(now|by|before|today)|call for (applications|proposals|papers|nominations)|"
    r"registrations?\s+(are\s+)?open|register\s+(now|by|before)|invites?\s+applications|invites?\s+(students|researchers|youth)|"
    r"last date|deadline|open to (all )?(students|researchers|graduates)|enrol\w*\s+(now|open)|"
    r"(will|to)\s+(host|organi[sz]e|conduct)|upcoming|calls? for)\b", _I)
_OPP_LAUNCH = re.compile(r"\b(launch\w*|announce\w*|offers?|introduc\w+|opens?)\b.{0,50}\b(fellowships?|internships?|scholarships?)\b", _I)
_DEADLINE = re.compile(r"(?:last date|deadline|apply (?:by|before)|till|until|before)\W+(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\.?(?:,?\s+\d{4})?)", _I)

# ------------------------------------------------------------- exclusions ---
_OPINION = re.compile(r"^\s*(opinion|editorial|column|letters?|podcast|watch|video|photos?|in pics|quiz)\b\s*[:|\-–—]?", _I)
_CRIME = re.compile(r"\b(arrest\w*|fraud\w*|scam\w*|duped|cheat\w*|FIR|murder\w*|killed|suicide|accident|crash\w*|extort\w*|blackmail\w*|cyber ?crime|rape|harass\w*|obscene|morphed)\b", _I)
_MARKET = re.compile(r"\b(shares?|stocks?|sensex|nifty|ipo|quarterly|q[1-4] (results|earnings)|earnings|smartphones?|price (cut|hike)|stock price|market cap|valuation|raises? \$|series [a-d]\b|unicorn|layoffs?|stake|revenue growth|iphone|samsung|launch(es)? (the )?(new )?\w+ (phone|laptop|tv))\b", _I)
_PUBLIC_ACTOR = re.compile(
    r"\b(government|govt|governor|minister|ministry|cabinet|chief minister|\bcm\b|state|department|directorate|"
    r"commission(er)?|assembly|legislat\w+|mission|panchayat|municipal\w*|corporation|authority|administration|"
    r"police|high court|supreme court|court|collector|district|council|secretariat|board|task ?force|"
    r"university|universities|institute|iit|iisc|iiser|iiit|aiims|college|centre of excellence|center of excellence|"
    r"nasscom|stpi|meity|niti|bhashini|indiaai|digital india|public sector|psu|e-?governance)\b", _I)


@dataclass
class Classification:
    category: str | None
    confidence: str
    sector: str
    record_type: str                       # activity | opportunity
    opportunity_type: str | None
    deadline: str | None
    scores: dict[str, float] = field(default_factory=dict)
    fired: list[str] = field(default_factory=list)


def score_categories(text: str) -> tuple[dict[str, float], list[str]]:
    scores, fired = {}, []
    for cat, rules in _COMPILED.items():
        hits = []
        for pat, w in rules:
            if pat.search(text):
                hits.append(w)
                fired.append(f"{cat}:{pat.pattern[:50]}")
        # Diminishing returns: strongest rule counts fully, others half. Stops several
        # overlapping patterns describing ONE idea from outvoting a single decisive rule.
        hits.sort(reverse=True)
        scores[cat] = (hits[0] + 0.5 * sum(hits[1:])) if hits else 0.0
    return scores, fired


def detect_sector(text: str) -> str:
    counts = {k: len(p.findall(text)) for k, p in _SECTOR_C.items()}
    best = max(counts.items(), key=lambda kv: kv[1])
    return best[0] if best[1] > 0 else "none"


def detect_opportunity(text: str) -> tuple[str | None, str | None, str | None]:
    """(opportunity_type, deadline_iso, deadline_note). Needs both a type word AND a forward-looking cue."""
    otype = next((t for t, p in _OPP_TYPE if re.search(p, text, _I)), None)
    if not otype:
        return None, None, None
    if not (_OPP_FORWARD.search(text) or _OPP_LAUNCH.search(text)):
        return None, None, None            # past-tense news about a workshop is an activity, not an opportunity
    m = _DEADLINE.search(text)
    deadline = None
    if m:
        d = normalize_date(m.group(1))
        deadline = d.iso if d.precision == "day" else None
    return otype, deadline, None


def classify(text: str) -> Classification:
    scores, fired = score_categories(text)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], TIE_PRECEDENCE.index(kv[0])))
    (top, s1), (_, s2) = ranked[0], ranked[1]
    sector = detect_sector(text)
    otype, deadline, _ = detect_opportunity(text)
    if s1 <= 0:
        return Classification(None, "low", sector, "activity", None, None, scores, fired)
    margin = s1 - s2
    conf = "high" if (s1 >= 3 and margin >= 2) else "medium" if (s1 >= 2 and margin >= 1) else "low"
    if otype:
        return Classification("education_opportunities", conf if s1 else "medium", sector, "opportunity",
                              otype, deadline, scores, fired)
    return Classification(top, conf, sector, "activity", None, None, scores, fired)


def screen(title: str, description: str) -> tuple[bool, str]:
    """Pre-state inclusion screen on text alone. Returns (keep, reason_code)."""
    text = f"{title}. {description}".strip()
    if not is_ai_related(text):
        return False, "not_ai_related"
    if _OPINION.search(title):
        return False, "opinion_or_commentary"
    return True, "ok"


def state_is_subject(title: str, evidence: str | None) -> bool:
    """True if the state name opens the headline ('Telangana signs...', 'Kerala to...'): the
    state itself is then the actor even without the word 'government'."""
    if not evidence:
        return False
    i = title.casefold().find(evidence.casefold())
    return 0 <= i <= 12


def screen_after_classification(title: str, description: str, c: Classification,
                                state_subject: bool = False) -> tuple[bool, str]:
    text = f"{title}. {description}"
    if c.category is None:
        return False, "no_category_match"
    strong = max(c.scores.values()) >= 3
    if _CRIME.search(title) and not (strong and c.category in ("policy_governance", "research_institutions", "education_opportunities")):
        return False, "crime_or_scam_story"
    if _MARKET.search(title) and c.category not in ("policy_governance",):
        return False, "market_or_product_news"
    if not (state_subject or _PUBLIC_ACTOR.search(text)):
        return False, "no_public_actor"
    return True, "ok"
