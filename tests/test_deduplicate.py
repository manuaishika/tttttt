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
