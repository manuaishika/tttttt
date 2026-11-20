"""Stage cue: what the HEADLINE's wording says about how far an activity has progressed.

    proposed_or_planned       "Kerala to set up...", "plans", "eyes", "draft", "will"
    announced_or_approved     "approves", "clears", "signs MoU", "unveils", "launches policy"
    implemented_or_operational"rolls out", "deployed", "inaugurated", "goes live", "uses AI to..."
    unclear                   nothing decisive in the headline

This is a reading of the headline's verbs, NOT an assessment of maturity or of what is
actually happening on the ground. It is useful for separating plans from announcements
from things already running, and it is labelled as such everywhere it is shown.

Precedence: completed implementation verbs > announcement/approval verbs > future or
intention wording > present-tense use. Verbs preceded by 'to'/'will' (e.g. "plans to
deploy") are treated as intentions, not completed actions.
"""
from __future__ import annotations
import re

STAGES = {
    "proposed_or_planned": "Proposed / planned",
    "announced_or_approved": "Announced / approved",
    "implemented_or_operational": "Implemented / in operation",
    "unclear": "Stage unclear",
}

_NOT_FUTURE = r"(?<!\bto )(?<!\bwill )(?<!\bwould )(?<!\bplans to )"
_IMPLEMENTED = re.compile(_NOT_FUTURE + r"\b(rolls? out|rolled out|deployed|deploys|operationali[sz]ed|now operational|"
                          r"goes live|went live|inaugurat\w+|commission(s|ed)|installed|in use|put to use|"
                          r"has (started|begun|deployed)|began|starts using|started)\b", re.I)
_ANNOUNCED = re.compile(_NOT_FUTURE + r"\b(approves?|approved|clears?|cleared|nod|green ?light|announces?|announced|"
                        r"unveils?|unveiled|notif(y|ies|ied)|signs?|signed|inks?|inked|mous?|pact|launch(es|ed)?|"
                        r"constitutes?|constituted|forms?|formed|releases?|released|adopts?|adopted|sanctions?|"
                        r"sanctioned|allocates?|allocated|earmarks?|earmarked|sets up|set up|establishe[sd]|okays?|okayed|"
                        r"bars?|barred|bans?|banned|restricts?|mandates?|directs?|orders?|partners?|partnered|"
                        r"ties up|teams up|joins? hands|collaborates?)\b", re.I)
_PLANNED = re.compile(r"\b(plans?|planned|planning|proposes?|proposed|proposal|mulls?|considering|eyes|eyeing|aims? (to|at)|"
                      r"aiming (to|at)|wants? to|draft|soon|upcoming|in the works|under review|in final stage|vision|roadmap|"
                      r"will|set to|to (set up|build|launch|introduce|establish|create|develop|use|deploy|roll out|"
                      r"get|host|train|enforce|start|adopt|unveil|make|become|bring|open|invest|provide|offer))\b", re.I)
_PRESENT_USE = re.compile(r"\b(uses?|using|leverag\w+|taps?|harness\w*|deploys?)\b.{0,40}\b(ai|artificial intelligence)\b|"
                          r"\bai[- ](powered|based|enabled)\b.{0,40}\b(cameras?|system|portal|platform|app)\b", re.I)


def stage_cue(title: str) -> str:
    t = title or ""
    if _IMPLEMENTED.search(t):
        return "implemented_or_operational"
    if _ANNOUNCED.search(t):
        return "announced_or_approved"
    if _PLANNED.search(t):
        return "proposed_or_planned"
    if _PRESENT_USE.search(t):
        return "implemented_or_operational"
    return "unclear"
