# Requirements checklist

Translated from the assignment brief (screenshots) and the project brief.
Status: `[x]` done, `[~]` in progress, `[ ]` not started. This file is updated as the project evolves.

## Mandatory deliverables (assignment brief)

| # | Deliverable | Where | Status |
|---|-------------|-------|--------|
| 1 | Dataset (CSV or XLSX) of structured records | `data/processed/*.csv`, `*.xlsx` | [ ] |
| 2 | Live public webpage, link in docs | `dashboard/` + deployment link in README | [ ] |
| 3 | Git repo with frequent, meaningful commits | this repo | [~] |
| 4 | Code as a runnable zip | `make zip` / `scripts/make_zip.sh` | [ ] |
| 5 | Rationale note and READMEs | `README.md`, `docs/rationale.md` | [~] |

## Dataset requirements

- [ ] Per record: state, headline, date, source name, source URL, one-line summary, category
- [ ] Consistent schema (see `src/schema.py`) — narrow and clean beats wide and messy
- [ ] Separate logical datasets: ecosystem **activities** and **opportunities**

## Key pointers from the assignment

- [ ] **Prioritise, don't cover everything.** Discovery sweep over all 28 states + 8 UTs, deeper coverage driven by evidence, with the prioritisation shown in the data (`state_coverage.csv`).
- [ ] **Deduplicate** cross-outlet duplicates (`src/deduplicate.py`), keeping a map of what was collapsed.
- [ ] **Normalise dates and states** (`src/normalize.py`): "UP" / "Uttar Pradesh" / "Uttar-Pradesh" → one state; missing and approximate dates handled explicitly.
- [ ] **Sourcing is documented**: what was used and why, stubs/limits disclosed (`docs/source-registry.md`, `docs/limitations.md`).
- [ ] **Assumptions and known holes** disclosed in the README / `docs/limitations.md`.
- [ ] **AI-tool usage** disclosed (the brief expects it): see README.
- [ ] **"How you drew the line"** — inclusion/exclusion criteria (`docs/methodology.md`) and an `excluded_records.csv` that shows what was rejected and why.

## Project-brief requirements

- [ ] Taxonomy of six categories (`docs/taxonomy.md`)
- [ ] Source registry (name, URL, type, relevance) — `data/processed/source_registry.csv`
- [ ] Source verification status per record; never fabricated; unverified marked explicitly
- [ ] Announcement date vs publication date kept distinct
- [ ] Traceability: each processed record → raw snapshot → source
- [ ] State-level assessment (0–3 per dimension, with evidence confidence and coverage) — `docs/benchmark-framework.md`, `src/assess.py`
- [ ] Gaps and recommendations, with observed facts separated from recommendations
- [ ] Dashboard: statistics, state distribution, filters, search, institutions, source links, India map, institution hotspots, opportunities section
- [ ] Map avoids rankings based solely on article counts
- [ ] Search architecture ready for semantic/hybrid later (documented; not built)
- [ ] Docs: README, methodology, rationale, taxonomy, benchmark-framework, source-registry, limitations

## Execution order (from the project brief)

1. [x] Inspect brief → checklist (this file)
2. [x] Repository + structure
3. [ ] Schema + taxonomy
4. [ ] State normalisation + validation
5. [ ] Collection pipeline
6. [ ] Deduplication + source verification
7. [ ] Real initial batch
8. [ ] Structured datasets
9. [ ] Dashboard + map
10. [ ] Test, document, deploy, package
