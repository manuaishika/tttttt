# Methodology

## 1. Collection
**Where from.** Two source families, chosen for *discovery breadth* with zero cost and no keys (full reasoning in `rationale.md`):

1. **Google News RSS search** — 6 themed queries × 36 states/UTs (policy, deployment, research, partnerships/investment, safety/ethics, education/opportunities) plus 4 pan-India opportunity queries, each with a 365-day window.
2. **Direct feeds** from publishers/government with real URLs and descriptions: PIB, MediaNama, ETGovernment, The Hindu, The Hindu BusinessLine, The Indian Express, Analytics India Magazine, Inc42 (recent items only).

**Rules followed.** No article page is fetched, no paywall touched, no robots-restricted area crawled; requests are throttled with jitter and identify themselves. Google News redirect tokens are **not decoded** (see limitations). The raw result is stored immutably in `data/raw/<date>/` with a fetch log, so processing is reproducible and every record points back via `raw_ref`.

## 2. Inclusion and exclusion — "how we drew the line"
A raw item becomes a record only if **all four** hold:

1. **AI-related** (headline/description mentions AI, machine learning, generative AI, LLM, chatbot, deepfake…). "Air India" / flight numbers like AI-171 are explicitly stripped first.
2. **State anchor** from the text, an institution, or a city (see §3).
3. **Public actor** — a government body, public institution, court, police, mission, research institution, or the state itself as sentence subject ("Telangana signs…"). Two documented exceptions: *opportunities* (whoever runs them) and *state-level AI infrastructure investments*.
4. **Activity cue** — at least one taxonomy rule fires (an announcement, deployment, partnership, research launch, safety/ethics move, or opportunity).

Excluded with a reason code in `excluded_records.csv`: `not_ai_related`, `opinion_or_commentary`, `crime_or_scam_story`, `market_or_product_news`, `no_public_actor`, `no_category_match`, `state_not_in_text`, `no_state_anchor`, `outside_time_window`, `exact_url_repeat`, `validation_failed:*`.

**Out of scope on purpose:** startup funding rounds, product launches, crime stories where AI is incidental, opinion pieces, national-only announcements with no state anchor, individual deepfake court orders (legal cases, not policy).

## 3. Normalisation
**States/UTs** (`normalize.py`, reference data in `reference.py`). 28 states and 8 UTs are kept separate. Structured input accepts canonical names, aliases (Orissa, Keralam, Pondicherry), hyphen/underscore/spacing variants and codes, so `UP`, `Uttar Pradesh`, `Uttar-Pradesh` → one state. Typos use a conservative fuzzy fallback (≥85 on full names only, ≥6 chars) and are flagged `fuzzy`.
**In free text**, only full names, aliases, cities and institutions count, plus a short list of unambiguous contextual abbreviations. State assignment order: **text → institution → city**. A query's state is a hint only. If several states appear, the one matching the query is chosen when mentioned, otherwise the first; the rest are noted in `state_evidence` ("also mentions…"). One state per record is a known simplification.
**Dates.** RFC-822/ISO/`5 March 2025`/`March 5, 2025`/day-first `05/03/2025`/`March 2025`/`2025` are parsed with explicit precision (`day|month|year|unknown`). Approximate wording ("early 2025", "Q3") and unparseable values become `unknown` with a note; future dates are rejected for publication dates (but allowed for deadlines). Year-less deadlines ("apply by April 26") are resolved to the first such date on/after the publication date — a stated rule, applied only when a publication date exists.
**Publication vs announcement date.** Feeds give only publication date. `announcement_date` is `not_determined` unless stated in text (never the case in this batch).

## 4. Classification (`classify.py`)
Weighted keyword/regex rules per category; per category the strongest rule counts fully and others half (so several patterns describing one idea cannot outvote one decisive rule). Highest score wins; near-ties are broken by a documented precedence (more specific categories first). `category_confidence` (high/medium/low) reflects score and margin. Sector is detected separately. **Opportunity** = an opportunity-type word (fellowship, internship, scholarship, workshop, hackathon, conference, summer school…) **plus** a forward-looking cue (applications open, apply by, registrations, eligibility, "to host"…); award stories ("X bags fellowship") and past events are activities. All fired rules are inspectable.

## 5. Deduplication (`deduplicate.py`)
1. Exact-URL repeats (same article through several queries) collapse first and are logged (`exact_url_repeat`) — they are not outlets corroborating each other.
2. Headlines are normalised (publisher suffix removed, abbreviations expanded, stop-words dropped).
3. Within a state block, two items link when `token_set_ratio ≥ 82`, `token_sort_ratio ≥ 65`, they share ≥3 meaningful tokens, and are ≤21 days apart.
4. Union-find gives clusters. The canonical item is chosen by source authority tier, then earliest date. Everything is kept in `duplicates.csv`.
**Trade-off:** thresholds are conservative — loosely reworded headlines of the same event can stay separate (a test documents this). 110 of 811 records are merged clusters; the largest merges 21 distinct articles.

## 6. Source classification and verification (`sources.py`)
Publisher type comes from domain first (`.gov.in`/`.nic.in` → government; `.ac.in` → academic), then reviewed lists (think tanks, established media), then name heuristics; anything else is `other_media`. Verification status:

| Status | Rule |
|---|---|
| `primary_source` | publisher is government/academic |
| `corroborated` | ≥2 distinct publishers in the cluster |
| `single_secondary_source` | one established media/think tank |
| `unverified` | unrecognised publisher, no corroboration |

This describes **support in the sources we hold, not a fact-check**. Source lists are hand-reviewed and extending them is an explicit code change.

## 7. Validation (`validate.py`)
Required fields; canonical state/UT only (`Pan-India` only for opportunities); ISO dates with explicit `unknown`; coordinates inside India; announcement-date status consistent; a record may not claim `primary_source` without an official publisher or `corroborated` without another publisher; opportunity fields complete. Failures go to the exclusion log.

## 8. Geography
`lat/lon` are set only when backed by the registry: an institution in the seed registry (47 entries, approximate campus coordinates) **in the record's own state**, else a registry city. Otherwise the record is state-level only (`geo_precision`). 53 records have institution-level and 73 city-level geography; the map (next milestone) will mark the rest at state level without fake precision.

## 9. Progressive search design
Records carry `record_id`, `title`, `summary`, `category`, `sector`, `state`, `institutions` so that keyword search + filters work now; an embedding column/vector index can be added keyed by `record_id`, with hybrid ranking (BM25 + vector) later. Multilingual search is a future extension (needs regional-language sources first). No vector infrastructure is built because it does not yet earn its place at this data size.
