# India AI Policy Tracker

A Python pipeline and Streamlit dashboard that track **AI policy and government activity across Indian states and union territories**: AI missions and policies, deployments in public services, research institutions, partnerships and investments, responsible-AI moves, and student opportunities.

Records are collected from news and official feeds, normalised, deduplicated across outlets, and labelled with **how strongly each is sourced**. Absence of evidence is never shown as absence of activity.

**Live dashboard:** https://worktest.streamlit.app

## Features
- Discovery across all 28 states and 8 UTs (Google News RSS, direct government and publisher feeds, optional GNews and NewsAPI)
- State/date normalisation, transparent inclusion rules, cross-outlet deduplication with an audit trail
- Provenance on every record: evidence status, link type (direct vs Google redirect), discovery channel, raw snapshot reference
- Separate datasets for **activities** and **opportunities**
- Dashboard in five sections: **Overview** (clickable India map + selected-state panel), **State Intelligence**, **Activity Explorer** (all-words search, filters, record detail with provenance), **Opportunities** (manually reviewed), **Methodology** (sources, coverage, downloads)

## Data (`data/processed/`)
| File | Contents |
|---|---|
| `activities.csv`, `opportunities.csv` | The two datasets (also in `ai_policy_activity.xlsx`) |
| `excluded_records.csv` | Every rejected item with its reason |
| `duplicates.csv` | Which reports were merged into each record |
| `source_registry.csv`, `state_coverage.csv`, `run_summary.json` | Sources, per-state research coverage, run counts |

Current dataset (collected 2026-11-20): **864 activities, 15 opportunities, 34 of 36 states/UTs**.

## Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
streamlit run dashboard/app.py          # dashboard on the committed data
pytest -q                               # tests
python -m src.pipeline                  # rebuild datasets from all raw snapshots
python -m src.collect                   # collect a fresh RSS snapshot
python -m src.collect --no-rss --apis gnews newsapi   # optional API discovery
```
API keys are optional. Copy `.env.example` to `.env` and set `GNEWS_API_KEY` / `NEWSAPI_KEY`; without them the RSS pipeline runs as normal. Never commit `.env`.

## Deploy
Streamlit Community Cloud (free): sign in at share.streamlit.io with GitHub → *New app* → this repository and branch → main file `dashboard/app.py`. No secrets are needed, because the app reads the committed datasets.

## Repository
```
src/            collect, connectors/ (gnews, newsapi), normalize, classify, deduplicate, validate, sources, pipeline
dashboard/      app.py, data.py, assets/india_states.geojson
data/raw/       immutable snapshots + fetch logs      data/processed/  published datasets
scripts/        build_boundaries.py (rebuilds the map asset)
docs/           methodology.md, limitations.md
tests/          pytest suite
```

## Documentation
- [Methodology](docs/methodology.md): sources, taxonomy, state prioritisation, classification, verification, deduplication
- [Limitations](docs/limitations.md): coverage gaps, data caveats, unresolved issues

Built with an AI coding assistant (Claude), as the assignment expects.
