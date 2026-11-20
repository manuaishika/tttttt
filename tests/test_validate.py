from datetime import date
from src import schema as S
from src.validate import validate_record, validate_records
from src.sources import classify_source, verification_for

TODAY = date(2026, 11, 20)


def good():
    return {
        "record_id": "r1", "record_type": "activity", "state": "Kerala", "state_code": "KL",
        "state_type": "State", "title": "Kerala sets up AI mission", "summary": "Kerala sets up AI mission",
        "summary_basis": "headline_only", "url_type": "publisher_direct", "discovery_sources": "google_news_rss", "stage_cue": "unclear", "geographic_scope": "state", "location_basis": "named_in_headline", "activity_stage": "undetermined", "category": "policy_governance", "sector": "none",
        "published_date": "2026-05-01", "date_precision": "day", "announcement_date": "",
        "announcement_date_status": "not_determined", "source_name": "The Hindu",
        "source_url": "https://example.org/a", "source_type": "established_media",
        "verification_status": "single_secondary_source", "verification_basis": "single source",
        "geo_precision": "none", "lat": "", "lon": "", "corroborating_sources": "",
    }


def errors(rec):
    return {(i.field) for i in validate_record(rec, TODAY) if i.severity == "error"}


def test_good_record_passes():
    assert errors(good()) == set()


def test_non_canonical_state_rejected():
    r = good(); r["state"] = "UP"
    assert "state" in errors(r)


def test_pan_india_only_for_opportunities():
    r = good(); r["state"] = S.PAN_INDIA; r["state_code"] = ""; r["state_type"] = ""
    assert "state" in errors(r)


def test_future_and_malformed_dates():
    r = good(); r["published_date"] = "2027-01-01"; assert "published_date" in errors(r)
    r = good(); r["published_date"] = "05/01/2026"; assert "published_date" in errors(r)


def test_missing_date_must_be_explicit():
    r = good(); r["published_date"] = ""; r["date_precision"] = "day"
    assert "published_date" in errors(r)
    r["date_precision"] = "unknown"; assert errors(r) == set()


def test_announcement_date_consistency():
    r = good(); r["announcement_date"] = "2026-04-01"
    assert "announcement_date" in errors(r)   # status says not_determined


def test_primary_source_requires_official_publisher():
    r = good(); r["verification_status"] = "primary_source"
    assert "verification_status" in errors(r)


def test_corroborated_requires_other_publishers():
    r = good(); r["verification_status"] = "corroborated"
    assert "verification_status" in errors(r)
    r["corroborating_sources"] = "NDTV"; assert errors(r) == set()


def test_coordinates_outside_india_rejected():
    r = good(); r.update(lat=51.5, lon=-0.1, geo_precision="city")
    assert "lat" in errors(r)


def test_duplicate_ids_rejected():
    valid, rejected, _ = validate_records([good(), good()], TODAY)
    assert len(valid) == 1 and len(rejected) == 1


def test_opportunity_requires_type():
    r = good(); r["record_type"] = "opportunity"
    assert {"opportunity_type", "deadline_status", "review_status"} <= errors(r)


def test_source_classification():
    assert classify_source("https://www.meity.gov.in")[0] == "government"
    assert classify_source("https://www.iitm.ac.in")[0] == "academic"
    assert classify_source("https://www.thehindu.com")[0] == "established_media"
    assert classify_source("https://www.impriindia.com")[0] == "think_tank"
    assert classify_source("https://random-blog.example")[0] == "other_media"


def test_verification_mapping_never_overclaims():
    assert verification_for("other_media", 1)[0] == "unverified"
    assert verification_for("established_media", 1)[0] == "single_secondary_source"
    assert verification_for("established_media", 3)[0] == "corroborated"
    assert verification_for("government", 1)[0] == "primary_source"


def test_google_redirect_must_be_labelled():
    r = good(); r["source_url"] = "https://news.google.com/rss/articles/CBMi123"
    assert "url_type" in errors(r)
    r["url_type"] = "google_news_redirect"; assert errors(r) == set()


def test_discovery_sources_and_summary_basis_controlled():
    r = good(); r["discovery_sources"] = "twitter"; assert "discovery_sources" in errors(r)
    r = good(); r["summary_basis"] = "llm_summary"; assert "summary_basis" in errors(r)
