# Methodology

## 1. Scope and taxonomy
The project tracks **AI policy and government activity** across Indian states and union territories (primary deliverable), plus related ecosystem activity and student opportunities. Each record gets one category and one sector.

| Category | What counts |
|---|---|
| AI policy and governance | AI policies, missions, task forces, regulatory frameworks, court/department AI-use rules |
| AI deployment and public infrastructure | AI used in public services: agriculture, health, education, policing, transport, administration |
| AI research and institutional development | Centres of excellence, labs, AI universities, compute/data-centre capacity, institute research |
| AI partnerships and investments | MoUs, government–industry/university collaborations, budgets, state-level AI investments |
| AI safety and responsible AI | Ethics, fairness, audit, risk governance, deepfake regulation |
| AI education and opportunities | Curricula and skilling; fellowships, internships, workshops, hackathons, conferences |

Sectors: agriculture, healthcare, education, environment, defence, policing & justice, infrastructure, public administration, none. Activities and opportunities are separate datasets (`activities.csv`, `opportunities.csv`).

## 2. Sources and collection
| Channel | Role | Notes |
|---|---|---|
| Google News RSS | Discovery (backbone) | 6 themed queries × 36 states/UTs + pan-India opportunity queries, 12-month window. Links are `news.google.com` redirects; headline only. |
| Direct RSS (PIB, MediaNama, ETGovernment, The Hindu, BusinessLine, Indian Express, AIM, Inc42) | Discovery + primary (PIB) | Real URLs and descriptions; recent items only. |
| GNews API, NewsAPI (optional, keyed) | Discovery + metadata enrichment | Direct publisher URLs and descriptions; free tiers reach back ~30 days, ~100 requests/day, no full text. Queries run in priority order (broad per state → pan-India topics → state × topic) and resume next run. |
| Official ministry/state/institute sites | Seed registry only | Not scraped; reachability recorded in `source_registry.csv`. |

Every run writes an immutable raw snapshot to `data/raw/<date>/` with a fetch log; processing reads only snapshots, so results are reproducible offline. No article pages are fetched, no paywalls touched, Google redirect tokens are not decoded, and API keys are read from environment variables only.

**Discovery ≠ verification.** The channel that found an item (`discovery_sources`) never changes its evidence status.

## 3. State prioritisation
No states were pre-selected. All 28 states and 8 UTs get identical queries; depth follows what is found. `state_coverage.csv` records, per state, how much was retrieved and how much passed, and labels each as *documented activity*, *limited evidence* or *no evidence found in this research*. The last is never read as "no activity".

## 4. Inclusion line
A raw item becomes a record only if **all** hold:
1. **AI-related headline** ("Air India"/flight numbers excluded). Judged on the headline for every channel, so API descriptions cannot admit stories with a passing AI mention.
2. **State anchor** from the headline (state name, unambiguous abbreviation such as "MP govt", registry institution, or city), falling back to the publisher description only if the headline has none. The query's state is never evidence.
3. **Public actor** (government, court, police, mission, university, research institute, or the state as subject), except for opportunities and state-level AI infrastructure investments.
4. **Activity cue**: a taxonomy rule fires.

Rejected items go to `excluded_records.csv` with a reason: `not_ai_related`, `state_not_in_text`, `no_state_anchor`, `no_public_actor`, `no_category_match`, `crime_or_scam_story`, `commentary_or_profile`, `market_or_product_news`, `opinion_or_commentary`, `outside_time_window`, `exact_url_repeat`, `validation_failed:*`.

## 5. Normalisation
- **States**: canonical names for 28 states + 8 UTs; aliases (Orissa, Keralam, Pondicherry), spacing/hyphen variants and codes for structured input (`UP` = `Uttar-Pradesh` = `Uttar Pradesh`); conservative fuzzy fallback. In free text, bare `MP`/`AP`/`HP` and the "New Delhi" dateline are not state evidence.
- **Dates**: explicit precision (day/month/year/unknown); approximate wording is `unknown`, never guessed; future publication dates rejected. `published_date` is the source's publication date. `announcement_date` (when the activity happened) is `not_determined` for all records. Year-less deadlines are resolved to the first such date on/after publication.

## 6. Classification
Transparent weighted keyword rules (`src/classify.py`), scored on the headline with the description as fallback; strongest rule counts fully, others half; documented tie-break precedence; `category_confidence` from score and margin. **Opportunity** = a type word (fellowship, internship, workshop, hackathon, conference, summer school, free online training…) plus a forward-looking cue (applications open, apply by, eligibility, to host…); award stories and past events are activities.

## 7. Deduplication
1. URLs are canonicalised (host, tracking parameters, AMP/mobile variants), and exact repeats across queries and channels collapse first. These are logged and never count as corroboration.
2. Within a state, headlines are normalised and linked when rapidfuzz `token_set_ratio ≥ 82`, `token_sort_ratio ≥ 65`, ≥3 shared tokens, ≤21 days apart.
3. Opportunities also merge when they share a distinctive programme-name token (e.g. "IndiaAI"), same type and state, ≤45 days apart.
4. The canonical record is the most authoritative source, then a direct publisher URL over a Google redirect, then one with a description, then earliest. Every merge is in `duplicates.csv`.
Thresholds deliberately under-merge.

## 8. Source classification and evidence status
Publisher type from domain (`.gov.in`/`.nic.in` → government, `.ac.in` → academic), then reviewed lists (think tanks, established media), else *unclassified*.

| Evidence status | Rule |
|---|---|
| Primary source | publisher is government or academic |
| Corroborated | ≥2 distinct publishers in the merged cluster |
| Single secondary source | one established outlet or think tank |
| Unverified | unrecognised publisher, no corroboration |

This is support in the sources held, **not a fact-check**; no record is manually verified. A working link is not verification. `url_type` distinguishes direct publisher links from Google News redirects; `summary_basis` distinguishes publisher descriptions from headline-only records.

## 9. Validation
`src/validate.py` enforces canonical states, ISO dates with explicit precision, coordinates inside India, controlled vocabularies (`url_type`, `summary_basis`, `discovery_sources`), consistent announcement/deadline fields, and that `primary_source`/`corroborated` claims are earned. Failures are excluded with the reason. Tests assert that `run_summary.json`, the CSVs and the XLSX report the same counts.

## 10. Geography and map
Coordinates are set only from the project's institution registry (47 entries, approximate campus locations) or city table, and only when consistent with the record's state; otherwise records are state-level. State boundaries come from a community dataset (udit-001/india-maps-data, pinned commit `2884453`, SHA-256 checked) dissolved to 36 states/UTs and validated against canonical names; it shows India's official external boundary but is not a Survey of India product. If the asset fails validation, the map falls back to labelled approximate points.

## 11. Search
Keyword search over headlines, publisher descriptions, institutions, sources and places, combined with state, category, sector, evidence and date filters. Records carry stable `record_id`s so semantic/hybrid retrieval can be added later without schema changes; it is not built.
