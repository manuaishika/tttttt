# Methodology

## 0. Conceptual Framework: Defining and Mapping India's AI Ecosystem
This is an **intelligence and landscape-mapping system for India's AI ecosystem**, with particular attention to AI governance and AI safety. News is a discovery channel, not the object of measurement. Status markers: **[implemented]**, **[partial]**, **[proposed]**.

**0.1 What counts as an AI activity [implemented as rules; see §4].** An identifiable action, commitment, proposal, institutional development, research output, collaboration, deployment, governance intervention or opportunity involving AI, undertaken, announced, proposed or materially advanced by an identifiable actor. Four tests: an identifiable actor, an identifiable action, a substantive link to AI, and evidence another researcher can follow. A passing mention of AI in a speech does not qualify; a minister announcing that a state will set up an AI centre does, even before it exists. A press release is a *source format*, not an activity: an official release announcing a committee is evidence of an institutional action; one saying AI is important is not. Current limit: the actor test is applied through headline cues, so 391 of 878 state-level records name no identifiable actor in the headline and are retained with "actor not identified" rather than discarded.

**0.2 Category is not stage [implemented].** The six categories (§1) describe *what kind* of activity; lifecycle stage describes *how far* it has gone. They are stored separately.

**0.3 Lifecycle [partial].** `activity_stage`: discussed/signalled, proposed/announced, approved/constituted, under implementation, operational/implemented, completed/discontinued/on hold, undetermined; with `stage_confidence` and `stage_basis`. Assigned automatically only when an official publisher (confidence *medium*) or two or more publishers (*low*) report the step in the headline; ambiguous wording takes the lower stage; implementation is never inferred from an announcement. "Discussed", "under implementation" and "completed" require primary evidence and are only set through `config/stage_evidence.csv` (*high*), which is empty in this release. The older `stage_cue` remains as a separate, clearly labelled headline-wording indicator.

**0.4 Geographic attribution [implemented].** Three dimensions are kept apart: *activity location* (state named in the headline or description), *actor location* (registry location of a named institution; `actor_location`), and *geographic scope* (state, multi-state, national; `geographic_scope`). `location_basis` records which one the state assignment rests on; where it is the institution's own location the record says so, because an institution's base is not necessarily where the activity happens (two records were re-attributed from Assam and Maharashtra to Arunachal Pradesh on this basis; institution names such as "IIT Delhi" are masked before reading state names, so they count as actor location, not activity location). National initiatives by Union bodies form a separate dataset and are **not** assigned to Delhi. Multi-state records keep one primary state plus `states_mentioned`, without duplicating the activity.

**0.5 Government and institutional classification [partial].** Actor *identity* (`actor_classes`): Union ministry/department, Union government (unspecified), state/UT government, local government, policy/advisory body, regulator/statutory authority, legislature, judiciary, public research institution, public implementation agency/mission, university/research institute, AI lab/technology company, industry association, think tank/civil society, international organisation. Identity is kept apart from *authority*: the legal or administrative basis is stated only for bodies in the curated registry (`config/actor_registry.csv`, e.g. "statutory regulator under the TRAI Act 1997"); for everyone else it is not asserted. The registry is small and hand-checked; most identifications come from generic cues ("cabinet", "High Court"), which give type and level but not the specific body.

**0.6 AI safety vs general AI research [partial].** AI safety and responsible AI (robustness, alignment, evaluations, interpretability, fairness, accountability, audit, risk management, deepfake regulation) is its own category, separated from general AI research by keyword rules. Coverage of technical safety research (papers, evaluations) is weak because discovery is news-based.

**0.7 Stakeholder and institutional landscape [partial].** `stakeholders.csv` lists registry organisations that appear as actors in at least one record, with type, level, location, stated authority, linked records, focus areas derived from those records, official website, website reachability and check date. No individuals, no private contact details, no unsupported entries. **Not yet implemented:** relationship layer (organisation-announced-initiative, institution-operates-centre, researcher-authored-paper), researcher profiles, verified public contact routes, think tanks and safety groups that never appear in news headlines.

**0.8 Monitoring and continuity [proposed].** Not implemented. The design would track official ministry and state department pages and feeds, institutional announcements and publications, laboratory blogs, consultations and fellowship calls, recording `last_checked`, latest evidence date and monitoring source per item. Until then, publication date is not activity status, and no programme is presented as active merely because no closure was found.

**0.9 Regional intelligence briefs [implemented].** The Overview lists, for India nationally and for Northern, Southern, Western, Eastern and Northeastern India (grouping adapted from the Zonal Councils; see the app), records whose source was published in a chosen window (30 days to 12 months, as of the collection date). Each item shows actor, headline, state or scope, category, evidence-based stage if known, publication date, publisher and evidence status. Ordering: well-sourced first, then actor identified, number of reports and recency. Regions with no qualifying records say so; there is no fixed number of items and no added significance claim.

**0.10 Evidence and confidence [implemented].** Evidence status (§8) describes support in the sources held, not truth; no record is manually fact-checked. Media coverage, actual ecosystem activity and institutional maturity are three different things; this collection measures the first and offers leads on the other two.

**0.11 Why this matters for AI security research and policy engagement.** The aim is to show who is driving AI governance and safety-relevant activity in India, where, at what stage and on what evidence: which Union and state bodies, regulators and courts are acting on AI; which institutions are building research capacity; where frontier labs and technology companies are partnering with public bodies; and which opportunities exist for researchers. That supports identifying engagement pathways and collaborators, while keeping every claim traceable to its source.

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

**Stage cue.** Each record also carries `stage_cue` (proposed/planned, announced/approved, implemented/in operation, unclear) read from the headline's verbs only (`src/stage.py`; e.g. "plans to", "approves", "rolls out"). It separates plans from announcements from things reported as running; it is not a maturity assessment.

**Opportunity review.** The 15 opportunities were reviewed manually on 2026-11-20; the result is a dated annotation in `config/opportunity_review.csv` (12 valid, 1 borderline, 2 not an opportunity), joined as `review_status`/`review_note`. No record is removed.

**Opportunity details from source text.** `python -m src.enrich_opportunities` tries to read each opportunity's original article and extracts, each with its exact supporting sentence: application deadline, programme/event dates, eligibility, fees/stipend, mode/location, application URL and organiser (`opportunity_enrichment.csv`, joined into `opportunities.csv`; the headline-derived `deadline` is kept unchanged). Publisher URLs come from direct links on the record or its merged reports, then an exact-headline lookup in GNews/NewsAPI (≈30-day window); Google News redirect tokens are not decoded. `robots.txt` must allow both generic and AI agents (ClaudeBot, GPTBot). A date is a deadline only after an explicit cue ("last date to apply/submit", "applications close", "apply by", "deadline", "registration closes"), with no programme/event wording between cue and date; publication and programme dates are never deadlines. Confidence: high (explicit cue, full date), medium (year inferred from publication date), low (weak "open till" cue). Status: `extracted`, `conflict` (sources or headline disagree; not resolved), `not_stated_in_accessible_sources` (article read, no deadline), `source_restricted` (robots.txt), `source_inaccessible` (no publisher URL or fetch failed), `not_checked`. Reviewer-supplied excerpts (`config/opportunity_evidence.csv`) go through the same extractor and are labelled. Deadline status is reported relative to the collection date.

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

## 11. Dashboard and search
Five sections: **Overview** (map of reporting volume, category breadth or well-sourced records, with a selected-state panel), **State Intelligence** (activity by area and stage, records, institutions and publishers), **Activity Explorer**, **Opportunities** (grouped by review status; deadline status only from stated dates, as of the collection date) and **Methodology** (registry, coverage, downloads). Explorer search runs across all of India by default (state-level and national records): every word must appear (AND), case-insensitive, partial words match, "quoted phrases" match exactly, across headline, publisher description, actors and actor types, institutions, publisher, state, city, region, category, sector, stage and evidence text. State selection is an optional narrowing filter; active filters are shown as chips with a clear-all action, and the results map shows where matches are attributed (national records counted separately). Category, actor-type and trend charts are clickable: a click opens Activity Explorer filtered to exactly that slice (state + category, category, actor type, or month + category), with a banner to go back to the originating chart or clear. Each record opens a detail view with its full provenance, including the reports merged into it. Records carry stable `record_id`s so semantic/hybrid retrieval can be added later without schema changes; it is not built.
