# Source registry

The machine-readable registry is `data/processed/source_registry.csv` (regenerated each run). Columns: `source_name, publisher_url, domain, source_type, source_tier, classification_reason, candidate_items, records_in_dataset, role, origin`.

It has two parts:
1. **Observed sources** — every publisher that appeared in collection (first batch: 246), classified by the rules in `src/sources.py`.
2. **Seed sources** (`config/seed_sources.csv`) — official/institutional sites reviewed up front, each with how it is (not) collected and a **reachability check** from the collection environment.

## Tiers
| Tier | Type | Role in this project |
|---|---|---|
| 1 | `government`, `academic` | Primary sources. A record published by one is `primary_source`. |
| 2 | `think_tank` | Secondary analysis; used for context and discovery |
| 3 | `established_media` | Discovery and corroboration |
| 4 | `other_media` | Discovery only; records are `unverified` unless corroborated |

## What was actually used
| Source family | How | Why |
|---|---|---|
| Google News RSS | 6 themed queries × 36 regions + 4 pan-India | Free, no key, date-windowed, broad cross-outlet discovery |
| PIB, MediaNama, ETGovernment, The Hindu, BusinessLine, Indian Express, AIM, Inc42 | direct RSS | Real URLs + descriptions; policy/government-tech focus |
| Official ministry/state/institute sites | **seed list only; not scraped** | Primary but heterogeneous; scrapers are a next milestone. Reachability is recorded honestly |

## Principles
* Prefer primary sources; use media for discovery and corroboration.
* Do not bypass paywalls or restrictions; nothing behind a login is touched.
* Preserve URLs and publication dates exactly as obtained.
* An unrecognised publisher is `other_media` → `unverified`. Credibility is never assumed.
