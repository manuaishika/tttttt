# Limitations

Figures refer to the current dataset (collected 2026-11-20): 878 state-level activities, 25 national-scope activities, 15 opportunities, 49 stakeholder entries.

## Evidence and content
- **Mostly single-source.** 561 records rest on one established outlet and 155 on an unrecognised publisher; only 43 are primary-source and 120 corroborated. No record has been manually fact-checked.
- **Headline-only records.** 793 of 879 records have no publisher description (Google News RSS gives none). They are labelled `headline_only`; the headline is not presented as a summary.
- **Redirect links.** 794 records link via `news.google.com` redirects (labelled `google_news_redirect`); the original publisher URL is not stored for these. Direct links exist for 85.
- **No event dates.** Only publication dates are known; `announcement_date` is `not_determined` everywhere. Trends are by publication month.
- **One state per record.** Multi-state stories are assigned to one state; others are noted in `state_evidence`.
- **Stage cues read headline verbs only** (proposed / announced / implemented / unclear; 305 records unclear). A headline saying "launches" may describe a ceremony rather than a running service; the label is not a maturity assessment.
- **Classification is keyword-based** and unevaluated against a labelled set. Manual audits of samples, not measured precision/recall, guided the rules. Known misses: headlines naming only a politician (e.g. a chief minister by name), and reworded duplicates that stay separate.

## Actors, geography, stage and national scope
- **Actors are identified from headlines only.** 391 of 878 state-level records name no identifiable actor; generic cues ("cabinet", "High Court") give type and level, not the specific body. Legal authority is stated only for 18 curated registry bodies.
- **Activity stage is mostly undetermined** (792 of 878): it is assigned only when an official source (medium confidence) or 2+ publishers (low) report the step in a headline. No primary documents have been reviewed yet (`config/stage_evidence.csv` is empty), so no stage has high confidence and "discussed", "under implementation" and "completed" are never assigned.
- **National-scope coverage is thin** (25 records): discovery queries were built per state, so Union-level activity enters only incidentally. Two weak items remain (a generic "India AI Mission and Emerging AI Ecosystem" piece and an award story).
- **Regions** are a documented convention adapted from the Zonal Councils, not an official five-way division.
- **Corrections in this release.** Missing aliases and cities (Arunachal, Jammu Kashmir, Great Nicobar; Calicut, Gorakhpur, Jammu, Kargil) were added. Two records attributed by an institution's own location were re-attributed to Arunachal Pradesh, one merged into an existing record of the same event and one under a new ID; IDs otherwise persist across re-clustering.

## Stakeholder directory
- Only registry organisations that appear as actors in at least one record (49). No individuals, no relationships layer, no verified contact routes beyond official websites. Websites are curated; on the last check 32 answered HTTP 200, 5 failed from the collection environment (403 or TLS errors; results vary between runs) and 12 company entries have no website curated. Think tanks and AI-safety groups that never appear in news headlines are absent.
- **Monitoring is not implemented**: nothing is re-checked automatically; "latest record date" is the latest source publication, not the organisation's current status.

## News APIs
- Free tiers return **only ~30 days** (GNews: 12-hour delay, 10 articles/request; NewsAPI: from 2026-10-19) and no full text. They cannot backfill the 12-month window, so the trend view excludes API-only records by default.
- One run used 85 requests per API: GNews returned 272 items and contributed to 59 published records (39 found by no other channel); NewsAPI returned 2,545 items and contributed to 23 records (21 found only by it). No API record failed validation.
- **API-only records are noisier.** A manual read of all 60 API-only records judged about 40 relevant (about 34 clearly), against noticeably higher precision for RSS records. The rest are mainly corporate, private-college or event stories that still pass the rules.

## Opportunities
- 15 records. A manual review (2026-11-20, `config/opportunity_review.csv`) labelled **12 valid**, 1 borderline (public access to a summit expo) and 2 not genuine openings (a summit report; a PR conference mentioning AI). They stay in the file with `review_status`; the dashboard separates them. New opportunities from future runs show as `not_reviewed` until reviewed.
- Opportunities come from news, not organiser websites. Coverage is a sample, not a directory; deadlines are shown only when stated, and many listings have closed.

## Opportunity details
- Checked 15 opportunities on 2026-11-20: **2 deadlines extracted with evidence** (IIT Roorkee, 29 Nov 2026, from a reviewer-supplied excerpt because Education Times' robots.txt disallows AI agents; UP AI Kaushal Hackathon, 20 Nov 2026, from two publisher pages, agreeing with its headline), **1 article read with no deadline** (Bennett summit report), **12 not verifiable**: only a Google News redirect was available, its token is not decoded, and the records are older than the news APIs' ~30-day window or not indexed by them. One of these (Anthropic fellowship) still shows the deadline stated in its headline, labelled as not verified against the article.
- Programme dates, eligibility, fees and mode are evidence sentences, not structured values; the application-URL heuristic can miss links.
- Reviewer-supplied excerpts are trusted as quoted; they carry the reviewer and date.

## Coverage bias
- English-language news only; regional-language media and state portals are largely invisible. States with more English coverage look more active. **Counts are not a ranking.**
- Dadra & Nagar Haveli and Daman & Diu and Lakshadweep have no records; that is an information gap, not evidence of no activity.
- Google News returns about 100 items per query, so high-volume states are truncated. Direct RSS feeds have no history.
- Official seed sites are not scraped; 5 of the 8 state portals probed (Karnataka, Tamil Nadu, Maharashtra, Odisha, Assam) were unreachable from the collection environment on the last check; reachability varies between runs.

## Technical
- **Map boundaries** come from a community dataset with no licence file and no accuracy guarantee (pinned and checksum-verified). It is not an authoritative Survey of India product.
- The institution registry has 47 hand-entered entries with approximate coordinates, so hotspots cover only registry institutions and 27 cities.
- Source-type lists are judgement calls.
- **Not implemented:** state-level 0–3 assessment scores, gap/recommendation analysis, semantic or multilingual search, portal scrapers.
- On narrow phone screens the map has blank space above and below it (Plotly keeps India's aspect ratio at a fixed height).
