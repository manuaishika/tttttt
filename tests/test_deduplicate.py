from src.deduplicate import normalize_title, cluster


_n = iter(range(10**6))


def it(title, state="Kerala", d="2026-05-01", pub="The Hindu", url=None):
    return {"state": state, "norm_title": normalize_title(title, pub), "published_date": d,
            "url": url or f"https://example.org/{next(_n)}"}


def test_publisher_suffix_stripped_and_abbrev_expanded():
    assert normalize_title("Kerala Govt approves AI mission - The Hindu", "The Hindu") == \
        normalize_title("Kerala government approves AI mission", None)


def test_same_story_different_outlets_cluster():
    items = [it("Kerala cabinet approves state AI mission - The Hindu"),
             it("Kerala cabinet nod for state AI Mission | NDTV", pub="NDTV", d="2026-05-02")]
    assert len(set(cluster(items))) == 1


def test_loosely_reworded_headline_is_conservatively_kept_separate():
    # Documented trade-off: prefer a leftover duplicate over merging two distinct events.
    items = [it("Kerala cabinet approves state AI mission"),
             it("Kerala government approves AI mission for governance", d="2026-05-02")]
    assert len(set(cluster(items))) == 2


def test_different_states_never_merge():
    items = [it("State cabinet approves AI mission", state="Kerala"),
             it("State cabinet approves AI mission", state="Gujarat")]
    assert len(set(cluster(items))) == 2


def test_same_title_far_apart_in_time_not_merged():
    items = [it("Kerala announces AI workshop for students", d="2026-01-01"),
             it("Kerala announces AI workshop for students", d="2026-09-01", url="u2")]
    assert len(set(cluster(items))) == 2


def test_distinct_events_stay_distinct():
    items = [it("Kerala signs MoU with Microsoft for AI skilling"),
             it("Kerala to use AI for crop disease detection")]
    assert len(set(cluster(items))) == 2


def test_exact_url_always_merges():
    items = [it("A b c", url="http://x"), it("Completely different", url="http://x", d="2020-01-01")]
    assert len(set(cluster(items))) == 1


def test_canonical_url_matches_same_article_across_channels():
    from src.deduplicate import canonical_url
    a = canonical_url("https://www.thehindu.com/news/kerala/ai-mission/article1.ece?utm_source=rss&utm_medium=x")
    b = canonical_url("http://m.thehindu.com/news/kerala/ai-mission/article1.ece/")
    assert a == b
    assert canonical_url("https://x.com/a?id=1") != canonical_url("https://x.com/a?id=2")   # real params kept


def test_canonical_prefers_direct_url_over_google_redirect_within_tier():
    from src.deduplicate import pick_canonical
    g = {"source_type": "established_media", "url_type": "google_news_redirect", "published_date": "2026-05-01", "has_description": False}
    d = {"source_type": "established_media", "url_type": "publisher_direct", "published_date": "2026-05-02", "has_description": True}
    gov = {"source_type": "government", "url_type": "google_news_redirect", "published_date": "2026-05-03", "has_description": False}
    assert pick_canonical([g, d]) is d
    assert pick_canonical([g, d, gov]) is gov   # authority still comes first
