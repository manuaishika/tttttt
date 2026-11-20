# India AI Ecosystem Intelligence

A small, reproducible pipeline that collects public reporting on **AI-related policy and ecosystem activity across Indian states and union territories**, cleans and classifies it, and presents it as structured datasets (and, next, a dashboard).

It is built to be more than a news aggregator: records keep their provenance, duplicates are collapsed with an audit trail, every exclusion has a reason code, and **absence of evidence is never presented as absence of activity**.

> **Status:** data pipeline, datasets, tests and docs are complete for the first batch. Dashboard, state-level assessment and deployment are the next milestones — see [`docs/checklist.md`](docs/checklist.md).
> **Live dashboard:** _not deployed yet_ (link will be added here).

## What is in the first batch

Collected 2026-11-20, 12-month window, English-language sources.

| | |
|---|---|
| Discovery queries | 228 (6 themes × 36 states/UTs + pan-India opportunity queries + 8 direct feeds) |
| Raw items retrieved | 5,662 |
| Published activity records | **811** (110 merged from multiple outlets) |
| Published opportunities | **19** |
| States/UTs with ≥1 record | 34 of 36 (`state_coverage.csv` says which have none, and why that is *not* proof of no activity) |
| Rejected items | 4,581, each with a reason code in `excluded_records.csv` |

## Datasets (`data/processed/`)

| File | Contents |
|------|----------|
| `activities.csv` | Ecosystem activity records (policy, deployment, research, partnerships, safety, education) |
| `opportunities.csv` | Fellowships, internships, workshops, hackathons, conferences (separate logical dataset) |
| `ai_policy_activity.xlsx` | Both datasets + coverage + source registry + taxonomy in one workbook |
| `excluded_records.csv` | Everything rejected, with `exclusion_reason` — shows *how the line was drawn* |
| `duplicates.csv` | Which raw items were merged into which record (`cluster_id`) |
| `source_registry.csv` | Every publisher seen (type, tier, why classified so) + reviewed seed sources with reachability |
| `state_coverage.csv` | Per state/UT: how much was retrieved vs. found, and an `evidence_status` |
| `run_summary.json` | Counts for the run |

Schema: [`src/schema.py`](src/schema.py). Minimum fields required by the brief (state, title, date, source name, source URL, summary, category) are all present, plus provenance fields (`verification_status`, `raw_ref`, `cluster_id`, `state_evidence`…).

## Architecture

```
config/discovery.json ─► collect.py ─► data/raw/<date>/<run>.jsonl   (immutable snapshot + fetch log)
                                              │
                    normalize.py ◄────────────┤   states, cities, institutions, dates
                    classify.py  ◄────────────┤   AI-relevance screen, category, sector, opportunity
                    deduplicate.py ◄──────────┤   exact-URL collapse, fuzzy cross-outlet clustering
                    sources.py   ◄────────────┤   publisher type + verification status
                    validate.py  ◄────────────┘   integrity rules; failures go to the exclusion log
                                              │
                                      pipeline.py ─► data/processed/*.csv, *.xlsx
```

Processing reads only the raw snapshot, so **any run can be reproduced offline**:

```bash
python -m src.pipeline --raw data/raw/2026-11-20/20261120T074546Z.jsonl
```

## Install & run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                                   # 79 tests
python -m src.pipeline                      # process the newest raw snapshot
python -m src.pipeline --collect            # collect fresh data, then process
python -m src.pipeline --check-seeds        # also probe official seed sites' reachability
python -m src.collect --regions Kerala      # collect a subset only
```

## Key design decisions (details in `docs/`)

* **Discovery first, depth second.** All 36 regions get the same six queries; depth is then driven by what is found (`state_coverage.csv`), not by assumed rankings.
* **A state is decided from the text**, never from which query returned the item. Items where only the query mentions the state are rejected (`state_not_in_text`) rather than guessed.
* **Abbreviations are dangerous.** "MP", "AP", "HP" appear in text as Member of Parliament, Associated Press, Hewlett-Packard. Only unambiguous contextual forms (`MP govt`, `in UP`, `A.P.`) count; bare "New Delhi" datelines are not "Delhi".
* **Dates are never invented.** Day/month/year precision is recorded; approximate wording becomes `unknown`. `published_date` ≠ `announcement_date`; the latter is `not_determined` for every record in this batch.
* **Verification status ≠ fact-check.** It states how well the claim is supported by sources we hold (`primary_source`, `corroborated`, `single_secondary_source`, `unverified`). No record is marked human-reviewed.
* **Rule-based classification, behind a stable interface**, so semantic/hybrid search can be added later without rebuilding.

## Known holes (full list: [`docs/limitations.md`](docs/limitations.md))

* **805 of 811 summaries are headline-only.** Google News RSS provides no snippet and its redirect links are not resolved (see limitations). Flagged per record in `summary_basis`.
* `source_url` for Google-sourced records is a `news.google.com` redirect, with the publisher's name and home page alongside; direct feed items have real URLs.
* English-language, news-derived: coverage reflects **media attention**, not actual activity. Do not read record counts as a ranking.
* Opportunities are sparse (19): fellowships are mostly announced on organisation websites, which are not yet crawled.
* No formal precision/recall evaluation yet; only an informal manual audit.
* 6 of 16 seed sites (6 of the 8 state portals) were unreachable from the build environment; state portals are not scraped.

## AI-tool usage disclosure

This project was built with an AI coding assistant (Claude) as the brief expects. The assistant wrote the code, tests and docs under direction; the design decisions listed above, the manual audits of sample output, and the tuning that followed from them are documented in the commit history.

## Repository layout

```
src/        collect, normalize, classify, deduplicate, validate, sources, pipeline, schema, reference
config/     discovery.json (queries & feeds), seed_sources.csv
data/raw/   immutable snapshots      data/processed/   published datasets and audit files
docs/       checklist, methodology, rationale, taxonomy, benchmark-framework, source-registry, limitations
tests/      pytest suite             dashboard/        (next milestone)
```
