"""Source classification and the source registry.

Classification is domain-first (a government domain is a government source regardless of
what the feed calls it), then name-based as a fallback. Unknown publishers are labelled
`other_media`, which downgrades the verification status to `unverified` — we never assume
credibility we have not established.
"""
from __future__ import annotations
import re
from urllib.parse import urlparse

GOV_SUFFIXES = (".gov.in", ".nic.in", ".gov", ".sansad.in")
ACADEMIC_SUFFIXES = (".ac.in", ".edu", ".edu.in", ".res.in")
# Hand-reviewed lists. Extending them is a deliberate, reviewable act (see docs/source-registry.md).
THINK_TANKS = {
    "orfonline.org", "carnegieindia.org", "carnegieendowment.org", "impriindia.com", "cprindia.org",
    "vidhilegalpolicy.in", "dakshindia.org", "thedialogue.co", "internetfreedom.in", "ai4bharat.org",
    "wadhwaniai.org", "nasscom.in", "iamai.in", "brookings.edu", "cyfyindia.com", "ccgnludelhi.wordpress.com",
}
ESTABLISHED_MEDIA = {
    "thehindu.com", "timesofindia.indiatimes.com", "indianexpress.com", "hindustantimes.com",
    "newindianexpress.com", "deccanherald.com", "thehindubusinessline.com", "business-standard.com",
    "livemint.com", "economictimes.indiatimes.com", "ndtv.com", "theprint.in", "scroll.in", "thewire.in",
    "medianama.com", "indiatoday.in", "news18.com", "telegraphindia.com", "tribuneindia.com",
    "deccanchronicle.com", "thesouthfirst.com", "financialexpress.com", "thenewsminute.com", "firstpost.com",
    "moneycontrol.com", "outlookindia.com", "ptinews.com", "ians.in", "theweek.in", "frontline.thehindu.com",
    "bhaskar.com", "livelaw.in", "barandbench.com", "mathrubhumi.com", "onmanorama.com", "thehansindia.com",
    "telanganatoday.com", "siasat.com", "orissapost.com", "odishatv.in", "sentinelassam.com", "eastmojo.com",
    "yourstory.com", "inc42.com", "techcircle.in", "analyticsindiamag.com",
    "timesnownews.com", "aninews.in", "devdiscourse.com", "newsonair.gov.in", "jagran.com", "dnaindia.com",
    "freepressjournal.in", "mid-day.com", "asianage.com", "thestatesman.com", "millenniumpost.in",
    "assamtribune.com", "nagalandpost.com", "morungexpress.com", "arunachaltimes.in", "northeasttoday.in",
    "pragativadi.com", "hindubusinessline.com", "cnbctv18.com", "zeebiz.com", "ibtimes.co.in", "wionews.com",
    "bwdisrupt.com", "bwbusinessworld.com", "expressinfra.in", "thetatva.in", "theindianexpress.com",
}
# Registered domains that look generic but are NOT credible-news evidence on their own.
UNCLASSIFIED_NOTE = "publisher not in reviewed source lists"

TIER = {"government": 1, "academic": 1, "think_tank": 2, "established_media": 3, "other_media": 4}


def domain_of(url: str | None) -> str:
    if not url:
        return ""
    host = urlparse(url if "//" in url else "//" + url).netloc.lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host


def _matches(host: str, suffixes: tuple[str, ...]) -> bool:
    return any(host.endswith(s) or host == s.lstrip(".") for s in suffixes)


def classify_source(publisher_url: str | None, source_name: str | None = None) -> tuple[str, str]:
    """Return (source_type, reason)."""
    host = domain_of(publisher_url)
    name = (source_name or "").casefold()
    if host:
        if _matches(host, GOV_SUFFIXES) and host not in ESTABLISHED_MEDIA:
            return "government", f"government domain ({host})"
        if _matches(host, ACADEMIC_SUFFIXES):
            return "academic", f"academic domain ({host})"
        base = ".".join(host.split(".")[-2:]) if not host.endswith((".co.in", ".com.pk")) else ".".join(host.split(".")[-3:])
        for h in (host, base):
            if h in THINK_TANKS:
                return "think_tank", f"reviewed think tank ({h})"
            if h in ESTABLISHED_MEDIA:
                return "established_media", f"reviewed media list ({h})"
        if any(host.endswith("." + m) for m in ESTABLISHED_MEDIA):
            return "established_media", f"subdomain of reviewed media ({host})"
    if re.search(r"press information bureau|\bpib\b|government of|\bgovt\b.*\bof\b|ministry of", name):
        return "government", f"name suggests official body ({source_name})"
    if re.search(r"\b(iit|iisc|iiser|iiit|university|institute of technology)\b", name):
        return "academic", f"name suggests academic body ({source_name})"
    return "other_media", UNCLASSIFIED_NOTE


def verification_for(source_type: str, distinct_publishers: int) -> tuple[str, str]:
    """Map evidence to a verification status. Never returns a 'verified' claim.

    The status describes how well the *claim is supported by the sources we hold*, not an
    independent fact-check. No record is marked human-reviewed unless a person did so.
    """
    if source_type in ("government", "academic"):
        return "primary_source", f"published by a {source_type} source itself"
    if distinct_publishers >= 2 and source_type != "other_media":
        return "corroborated", f"reported by {distinct_publishers} distinct publishers"
    if distinct_publishers >= 2:
        return "corroborated", f"reported by {distinct_publishers} distinct publishers (primary publisher unclassified)"
    if source_type in ("established_media", "think_tank"):
        return "single_secondary_source", f"single {source_type.replace('_', ' ')} source; no corroboration found"
    return "unverified", "publisher not in reviewed source lists and no corroboration found"
