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
SUMMARY_BASES = ["publisher_description", "headline_only"]
# How the record's URL relates to the article: a direct publisher link, or a Google News
# redirect (the original URL is not exposed by Google News RSS). A URL that resolves is NOT
# evidence that the claim is true - see verification_status for that.
URL_TYPES = ["publisher_direct", "google_news_redirect"]
# Discovery channels (how an item was FOUND). These say nothing about verification.
DISCOVERY_SOURCES = ["google_news_rss", "direct_feed", "gnews", "newsapi"]
GEO_PRECISIONS = ["institution", "city", "state", "none"]
CONFIDENCE_LEVELS = ["high", "medium", "low"]

# Special values for the `state` column
PAN_INDIA = "Pan-India"  # permitted for opportunities only (online / open to all states)
NATIONAL = "India (national)"  # national-scope activities (Union bodies, Parliament, Supreme Court); own dataset
GEOGRAPHIC_SCOPES = ["state", "multi_state", "national", "pan_india_opportunity"]
LOCATION_BASES = ["named_in_headline", "named_in_description", "actor_location_institution", "city_named",
                  "national_actor", "none"]
ACTIVITY_STAGES = ["discussed_signalled", "proposed_announced", "approved_constituted", "under_implementation",
                   "operational_implemented", "completed_discontinued_on_hold", "undetermined"]

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
    "summary_basis",             # publisher_description | headline_only (headline is NOT a summary)
    "source_description",        # publisher's own description/standfirst as supplied by feed/API
    "category",                  # (R) taxonomy key
    "sector",                    # sector key
    "category_confidence",       # high | medium | low (rule-match margin)
    "stage_cue",                 # headline wording: proposed / announced / implemented / unclear (src/stage.py)
    "activity_stage",            # evidence-gated lifecycle stage (src/stage.py: activity_stage) or undetermined
    "stage_confidence",          # high (primary document reviewed) | medium (official source) | low (2+ publishers) | ''
    "stage_basis",               # what the stage rests on
    "published_date",            # (R) ISO date the source published
    "date_precision",            # day | month | year | unknown
    "announcement_date",         # date the underlying event happened, if stated
    "announcement_date_status",  # stated | not_determined
    "source_name",               # (R) publisher
    "source_url",                # (R) URL as obtained from the feed/API
    "url_type",                  # publisher_direct | google_news_redirect
    "publisher_url",             # publisher home page, if provided by the feed
    "source_type",               # see SOURCE_TYPES
    "verification_status",       # see VERIFICATION_STATUSES
    "verification_basis",        # human-readable reason for the status
    "duplicate_count",           # number of raw items collapsed into this record
    "corroborating_sources",     # '|'-separated other publishers
    "cluster_id",                # links to duplicates.csv
    "state_evidence",            # text that justified the state assignment
    "states_mentioned",          # '|'-separated: every state named (multi-state support without duplicating records)
    "geographic_scope",          # state | multi_state | national | pan_india_opportunity
    "location_basis",            # named_in_headline | named_in_description | actor_location_institution | city_named | national_actor
    "actors",                    # '|'-separated actors named in the headline (src/actors.py)
    "actor_classes",             # '|'-separated, aligned with actors (identity, not authority)
    "actor_levels",              # '|'-separated: union | state | local | non_government | international | unknown
    "actor_location",            # registry-backed location of named institutions only ('City, State')
    "matched_query",             # which discovery query surfaced it
    "raw_ref",                   # pointer into data/raw snapshot (traceability)
    "discovery_sources",         # '|'-separated channels that surfaced any item in the cluster
    "collected_at",              # UTC timestamp of retrieval
]

OPPORTUNITY_EXTRA_COLUMNS = [
    "opportunity_type",          # fellowship | internship | ...
    "deadline",                  # ISO date if stated in the source, else empty
    "deadline_status",           # stated | not_stated
    "review_status",             # manual review (config/opportunity_review.csv) or not_reviewed
    "review_note",
]
STAGE_CUES = ["proposed_or_planned", "announced_or_approved", "implemented_or_operational", "unclear"]
REVIEW_STATUSES = ["valid", "borderline", "not_an_opportunity", "not_reviewed"]
OPPORTUNITY_COLUMNS = ACTIVITY_COLUMNS + OPPORTUNITY_EXTRA_COLUMNS

REQUIRED_NONEMPTY = [
    "record_id", "state", "title", "summary", "category",
    "source_name", "source_url", "verification_status",
]
