# Limitations and known holes

Stated plainly, because "what's broken" matters more than hiding it. Numbers refer to the first batch (collected 2026-11-20).

## Data quality
| # | Limitation | Impact | Mitigation / next step |
|---|---|---|---|
| 1 | **805 of 811 summaries are headline-only** (`summary_basis = headline_only`). Google News RSS has no snippet. | The "one-line summary" is mostly the headline, not a real summary | Direct feeds give real descriptions (6 records). Options: a keyed news API (GNews/NewsAPI) or crawling official pages. Not faked with generated text. |
| 2 | **`source_url` for Google-sourced records is a `news.google.com` redirect.** I did not decode the tokens (it reverse-engineers an undocumented endpoint and was judged out of bounds). | The original publisher URL is not stored for those; publisher name + home page are | Keyed news APIs return the real URL. Direct feeds already do. |
| 3 | **No formal evaluation.** Quality was checked by manual audits of ~100 sampled records/exclusions, not against a labelled set. Known false positives exist (e.g. a company literally named "Spintronics AI"; startup funding that slipped through the investment rule). | Precision/recall unquantified | Next step: hand-label ~200 records, report precision/recall per category and per exclusion reason |
| 4 | **Opportunities are sparse and noisy** (19; roughly two-thirds judged relevant on audit). Fellowships are announced on organisation sites, not in news. | The opportunities section is a sample, not a directory | Add crawlers/feeds for IndiaAI, IITs, AI-safety orgs; manually curate |
| 5 | **Classification is keyword-based.** Headlines without trigger words are missed (395 `no_category_match`); mixed stories take one category | Some real activity is absent; some labels are arguable | Semantic classification as a later iteration, evaluated against the same labelled set |
| 6 | **One state per record.** Multi-state stories keep the query's state if mentioned, else the first (14 records note "also mentions") | Slight undercount for multi-state items | Could emit one row per state |
| 7 | **Politicians' names are not mapped to states** ("Revanth Reddy suggests…") | Some state stories lack a text anchor and land in `state_not_in_text` (770) | Maintain office-holder lookup; entity linking |
| 8 | **`announcement_date` is never determined.** Only publication dates exist | Event date can differ from publication date | Extract from full text where legally accessible |

## Coverage bias
* **English-language news only.** Regional-language reporting and state-government portals (which often publish first, and in local languages) are largely invisible. States with more English media (Karnataka, Telangana, Maharashtra) look better than states with less, independent of real activity.
* **Counts measure media attention, not activity.** Do not rank states by record count. Coverage ≠ capability.
* **Absence of evidence ≠ absence of activity.** `state_coverage.csv` distinguishes `no_evidence_found_in_research` (Dadra & Nagar Haveli and Daman & Diu, Lakshadweep) from `limited_evidence`; neither claims nothing happens there.
* **Single 12-month snapshot**, one collection run. Google News returns ≤~100 items per query, so high-volume states are truncated.
* **Direct feeds return only recent items** (no history).
* **Unreachable official portals.** 6 of 16 seed sites — the Karnataka, Tamil Nadu, Kerala, Maharashtra, Odisha and Assam portals — timed out or errored from the build environment (`source_registry.csv`, column `origin`). This may be the environment's network rather than the sites. State portals are *not scraped* at all in this batch.

## Technical
* The institution registry is a 47-entry hand-curated seed with approximate campus coordinates, so institution-level hotspots exist for only 20 distinct institutions (53 records). City-level markers use a 27-city table.
* The "Pan-India" opportunity label means "not tied to a state"; it includes global programmes (e.g. company fellowships) that happen to be open to Indian applicants.
* The XLSX is regenerated from the CSVs on every run; hand edits would be overwritten.
* Source lists (`sources.py`) are judgement calls. Classifying a publisher as "established" says it is a long-standing outlet with editorial staff, not that every story is accurate.
* Verification status is **not** a fact-check. No record has been human-verified.

## Not built (deliberately)
Semantic/vector/hybrid search, multilingual search, per-state official-portal scrapers. The data model supports adding them without a rewrite (see `methodology.md` §9).
