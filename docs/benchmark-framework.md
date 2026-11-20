# State-level assessment framework (design; implementation in `src/assess.py` is the next milestone)

**Purpose.** Summarise *documented* AI activity per state/UT along six dimensions so researchers can see where evidence is strong, thin or missing. **It is not an official ranking and does not say any state is "best" at anything**, least of all AI safety.

## Dimensions
| Dimension | Drawn from categories |
|---|---|
| AI policy & governance | `policy_governance` |
| AI safety & ethics | `safety_responsible_ai` |
| Research & institutional development | `research_institutions` |
| Sectoral AI deployment | `deployment` (and `sector` spread) |
| Investments & partnerships | `partnerships_investment` |
| Talent development & opportunities | `education_opportunities` + `opportunities.csv` |

## Scores (qualitative, per dimension)
| Score | Meaning |
|---|---|
| 0 | No qualifying activity identified **in the research conducted** (not "no activity") |
| 1 | Emerging — isolated or announced-only activity |
| 2 | Developing — multiple distinct activities, or one backed by a primary source |
| 3 | Established — several distinct activities over time, including at least one primary-source or corroborated record, with evidence of implementation (not only announcement) |

Scores count **distinct clusters (events)**, never raw articles, so ten outlets covering one announcement still count once. Proposed first-pass thresholds on distinct events, then adjusted by the rules below: 0 → none; 1 → 1–2; 2 → 3–5; 3 → ≥6 across ≥2 months. Adjustments: cap at 2 if no primary or corroborated record; raise at most one level for a primary-source record of implementation; announcements alone cap at 2.

## Reported alongside every score
* **Evidence confidence** (high/medium/low): share of records that are primary/corroborated, number of independent publishers.
* **Research coverage** (high/medium/low): how much was retrieved for the state (`raw_items_retrieved_for_state_queries`) and source diversity. A `0` with *low* coverage is an **information gap**, a `0` with *high* coverage is a tentative **evidence-based gap** — still not proof of absence.
* Counts of distinct events, date range, and the records themselves (traceability).

## Presentation rules
* Show the matrix as dimensions × states with score, confidence and coverage; never a single composite rank.
* Observed facts and our recommendations are visually and textually separated.
* Colour never encodes article counts alone.

## Gaps and recommendations (separate output)
Each gap is labelled **evidence gap** (adequate coverage, low activity) or **information gap** (low coverage — we cannot tell). Recommendations (AI-safety research groups, governance workshops, fellowships, interdisciplinary collaborations) are labelled **our suggestion** and link to the gap that motivated them.

## Limitations
Scores inherit every limitation in `limitations.md` (English media bias, keyword classification, announcement-vs-implementation ambiguity). They are a research aid for orientation, to be validated against primary documents before any conclusion.
