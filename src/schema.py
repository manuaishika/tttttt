"""Single source of truth for the dataset schema and controlled vocabularies.

Every other module imports its enums and column lists from here, so a change to the
taxonomy or schema is made once. Values are plain strings (not Enum members) so they
serialise to CSV/JSON without conversion.
"""
from __future__ import annotations

# --- Taxonomy (see docs/taxonomy.md) ---------------------------------------
CATEGORIES = {
    "policy_governance": "AI policy and governance",
    "deployment": "AI deployment and public infrastructure",
    "research_institutions": "AI research and institutional development",
    "partnerships_investment": "AI partnerships and investments",
    "safety_responsible_ai": "AI safety and responsible AI",
    "education_opportunities": "AI education and opportunities",
}

# Sectors apply mainly to `deployment`, but any record may carry one.
SECTORS = {
    "agriculture": "Agriculture",
    "healthcare": "Healthcare",
    "education": "Education",
    "environment": "Environment & climate",
    "defence": "Defence & security",
    "policing_justice": "Policing & justice",
    "infrastructure": "Infrastructure & transport",
    "public_administration": "Public administration & services",
    "none": "Not sector-specific",
}

OPPORTUNITY_TYPES = [
    "fellowship", "internship", "scholarship", "workshop",
    "research_programme", "conference", "competition", "other",
]

RECORD_TYPES = ["activity", "opportunity"]

# --- Provenance & quality vocabularies -------------------------------------
SOURCE_TYPES = [
    "government",        # central/state government, departments, official policy documents
    "academic",          # IITs, IISERs, universities, research institutions
    "think_tank",        # think tanks, AI safety/governance organisations
    "established_media", # credible national/regional newspapers & established outlets
    "other_media",       # unclassified/unknown publisher
]

# Verification status is about *how well the claim is supported*, not whether it is true.
VERIFICATION_STATUSES = {
    "primary_source": "Record's source is an official government/institutional publisher",
    "corroborated": "Reported by 2+ independent publishers (cluster of duplicates)",
    "single_secondary_source": "One established media outlet; no corroboration found yet",
    "unverified": "Publisher not recognised or aggregator-only; treat with caution",
}

DATE_PRECISIONS = ["day", "month", "year", "unknown"]
ANNOUNCEMENT_DATE_STATUSES = ["stated", "not_determined"]
SUMMARY_BASES = ["feed_description", "headline_only"]
GEO_PRECISIONS = ["institution", "city", "state", "none"]
CONFIDENCE_LEVELS = ["high", "medium", "low"]

# Special values for the `state` column
PAN_INDIA = "Pan-India"  # permitted for opportunities only (online / open to all states)

# --- Dataset columns --------------------------------------------------------
# Order here is the column order in the CSV. Minimum set required by the brief is
# marked (R); the rest earn their place by supporting traceability or the dashboard.
ACTIVITY_COLUMNS = [
    "record_id",                 # stable hash of the canonical record
    "record_type",               # activity | opportunity
    "state",                     # (R) canonical state/UT name
    "state_code",                # ISO 3166-2:IN code, e.g. KL
    "state_type",                # State | Union Territory
    "city",                      # where determinable from text
    "institutions",              # '|'-separated registry institutions mentioned
    "lat", "lon", "geo_precision",  # only set from the institution/city registry
    "title",                     # (R) headline
    "summary",                   # (R) one-line summary
    "summary_basis",             # feed_description | headline_only
    "category",                  # (R) taxonomy key
    "sector",                    # sector key
    "category_confidence",       # high | medium | low (rule-match margin)
    "published_date",            # (R) ISO date the source published
    "date_precision",            # day | month | year | unknown
    "announcement_date",         # date the underlying event happened, if stated
    "announcement_date_status",  # stated | not_determined
    "source_name",               # (R) publisher
    "source_url",                # (R) URL as obtained from the feed
    "publisher_url",             # publisher home page, if provided by the feed
    "source_type",               # see SOURCE_TYPES
    "verification_status",       # see VERIFICATION_STATUSES
    "verification_basis",        # human-readable reason for the status
    "duplicate_count",           # number of raw items collapsed into this record
    "corroborating_sources",     # '|'-separated other publishers
    "cluster_id",                # links to duplicates.csv
    "state_evidence",            # text that justified the state assignment
    "matched_query",             # which discovery query surfaced it
    "raw_ref",                   # pointer into data/raw snapshot (traceability)
    "collected_at",              # UTC timestamp of collection
]

OPPORTUNITY_EXTRA_COLUMNS = [
    "opportunity_type",          # fellowship | internship | ...
    "deadline",                  # ISO date if stated in the source, else empty
    "deadline_status",           # stated | not_stated
]
OPPORTUNITY_COLUMNS = ACTIVITY_COLUMNS + OPPORTUNITY_EXTRA_COLUMNS

REQUIRED_NONEMPTY = [
    "record_id", "state", "title", "summary", "category",
    "source_name", "source_url", "verification_status",
]
