# Rationale (concise)

**Goal.** Understand where AI is being governed, researched, funded and deployed across Indian states — evidence-first, not a ranking.

**Sources.** Discovery needs breadth and no cost, so Google News RSS (many outlets, date windows) is the backbone, supplemented by direct government/publisher feeds that provide real URLs and descriptions. Official sites are the ideal primary sources but are heterogeneous and, in this first batch, partly unreachable; they are registered, not scraped. A keyed API (GNews/NewsAPI) was avoided to keep the project reproducible with no secrets, at the documented cost of headline-only summaries.

**State prioritisation.** No states were chosen up front. Every state and UT got the same six queries; depth follows evidence (`state_coverage.csv`): 28 states + 6 of 8 UTs produced records. Karnataka, Telangana, Odisha, Uttar Pradesh, Gujarat, Maharashtra and Bihar have the most documented activity, but that partly reflects English-language media attention, so the dashboard avoids ranking by count.

**Collection and cleaning.** One immutable raw snapshot per run; deterministic processing from it. State comes from the text, not the query. Duplicates are merged conservatively with a full audit trail. Every rejection has a reason code, so the inclusion line (AI + state anchor + public actor + activity cue) is inspectable.

**Classification.** Transparent keyword rules, not an LLM, because they are explainable, free, deterministic and fast to audit; the interface leaves room for a semantic classifier later.

**Visualisation (next milestone).** A state-level choropleth of *documented activity by category* with evidence-confidence shading, institution hotspots only where coordinates are registry-backed, filters, searchable records with source links, and a separate opportunities view. No rank-by-article-count.

**Stack.** Python, pandas, feedparser, rapidfuzz, CSV/XLSX, Streamlit + Plotly — the suggested stack was kept; nothing exotic was added because nothing exotic earned its place.
