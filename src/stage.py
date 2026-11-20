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


# --------------------------------------------------------------------------------------
# Evidence-gated lifecycle stage (separate from the headline cue above)
# --------------------------------------------------------------------------------------
ACTIVITY_STAGES = {
    "discussed_signalled": "Discussed / signalled",
    "proposed_announced": "Proposed / announced",
    "approved_constituted": "Approved / constituted",
    "under_implementation": "Under implementation",
    "operational_implemented": "Operational / implemented",
    "completed_discontinued_on_hold": "Completed / discontinued / on hold",
    "undetermined": "Undetermined",
}
_A_APPROVED = re.compile(_NOT_FUTURE + r"(?<!-)\b(approves?|approved|clears?|cleared|nod|okays?|okayed|notif(y|ies|ied)|"
                         r"constitutes?|constituted|sanctions?|sanctioned|signs?|signed|inks?|inked|mous?)\b", re.I)
_A_OPERATIONAL = re.compile(_NOT_FUTURE + r"\b(inaugurat\w+|rolls? out|rolled out|deployed|goes live|went live|"
                            r"operational|commission(s|ed))\b", re.I)
_A_PROPOSED = re.compile(r"\b(announc\w+|unveil\w*|launch\w*|propos\w+|plans?|planned|to set up|to establish|will)\b", re.I)


def activity_stage(title: str, verification_status: str, n_publishers: int,
                   manual: dict | None = None) -> tuple[str, str, str]:
    """(stage, confidence, basis).

    * A manual entry (config/stage_evidence.csv: reviewed primary document) wins: confidence 'high'.
    * Otherwise a stage is assigned ONLY if the step is reported by an official publisher
      (primary_source -> 'medium') or by 2+ independent publishers (corroborated -> 'low').
      Anything else is 'undetermined'.
    * Ambiguous wording gets the LOWER stage ('launches policy' -> proposed/announced).
      'Discussed', 'under implementation' and 'completed' are never inferred from headlines.
    """
    if manual:
        return manual["activity_stage"], "high", f"Primary evidence reviewed: {manual['evidence']}"
    if verification_status == "primary_source":
        conf, who = "medium", "headline of an official (government/academic) publication"
    elif verification_status == "corroborated":
        conf, who = "low", f"headline wording reported by {n_publishers} publishers"
    else:
        return "undetermined", "", "Single or unverified source: stage not assigned"
    for stage, pat in (("approved_constituted", _A_APPROVED), ("operational_implemented", _A_OPERATIONAL),
                       ("proposed_announced", _A_PROPOSED)):
        if pat.search(title or ""):
            return stage, conf, who
    return "undetermined", "", "No stage step stated in the well-sourced headline"
