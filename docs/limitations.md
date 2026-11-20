# Limitations

Figures refer to the current dataset (collected 2026-11-20): 864 activity records, 15 opportunities.

## Evidence and content
- **Mostly single-source.** 561 records rest on one established outlet and 155 on an unrecognised publisher; only 43 are primary-source and 120 corroborated. No record has been manually fact-checked.
- **Headline-only records.** 793 of 879 records have no publisher description (Google News RSS gives none). They are labelled `headline_only`; the headline is not presented as a summary.
- **Redirect links.** 794 records link via `news.google.com` redirects (labelled `google_news_redirect`); the original publisher URL is not stored for these. Direct links exist for 85.
- **No event dates.** Only publication dates are known; `announcement_date` is `not_determined` everywhere. Trends are by publication month.
- **One state per record.** Multi-state stories are assigned to one state; others are noted in `state_evidence`.
- **Classification is keyword-based** and unevaluated against a labelled set. Manual audits of samples, not measured precision/recall, guided the rules. Known misses: headlines naming only a politician (e.g. a chief minister by name), and reworded duplicates that stay separate.

## News APIs
- Free tiers return **only ~30 days** (GNews: 12-hour delay, 10 articles/request; NewsAPI: from 2026-10-19) and no full text. They cannot backfill the 12-month window, so the trend view excludes API-only records by default.
- One run used 85 requests per API: GNews returned 272 items and contributed to 59 published records (39 found by no other channel); NewsAPI returned 2,545 items and contributed to 23 records (21 found only by it). No API record failed validation.
- **API-only records are noisier.** A manual read of all 60 API-only records judged about 40 relevant (about 34 clearly), against noticeably higher precision for RSS records. The rest are mainly corporate, private-college or event stories that still pass the rules.

## Opportunities
- 15 records, of which a manual check judged **12 valid**, 1 borderline (public access to a summit expo) and 2 not genuine openings (a summit report; a PR conference mentioning AI). They remain in the file, unflagged by the pipeline.
- Opportunities come from news, not organiser websites. Coverage is a sample, not a directory; deadlines are shown only when stated, and many listings have closed.

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
- The live deployment depends on the hosting account (see README).
