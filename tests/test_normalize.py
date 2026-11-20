import pytest
from src.normalize import (normalize_state, extract_states, extract_cities,
                           extract_institutions, normalize_date)
from datetime import date

TODAY = date(2026, 11, 20)


@pytest.mark.parametrize("raw,expected", [
    ("UP", "Uttar Pradesh"), ("Uttar Pradesh", "Uttar Pradesh"), ("Uttar-Pradesh", "Uttar Pradesh"),
    ("uttar_pradesh", "Uttar Pradesh"), ("  UTTAR PRADESH ", "Uttar Pradesh"), ("UttarPradesh", "Uttar Pradesh"),
    ("Orissa", "Odisha"), ("OR", "Odisha"), ("Keralam", "Kerala"), ("Pondicherry", "Puducherry"),
    ("J&K", "Jammu and Kashmir"), ("Jammu & Kashmir", "Jammu and Kashmir"),
    ("Govt of Karnataka", "Karnataka"), ("NCT of Delhi", "Delhi"), ("New Delhi", "Delhi"),
    ("TN", "Tamil Nadu"), ("tamilnadu", "Tamil Nadu"), ("Telengana", "Telangana"),
    ("Maharashtara", "Maharashtra"),
])
def test_normalize_state_variants(raw, expected):
    assert normalize_state(raw).state == expected


@pytest.mark.parametrize("raw", ["", None, "Atlantis", "Texas", "xyz"])
def test_normalize_state_rejects_unknown(raw):
    assert normalize_state(raw) is None


def test_extract_states_free_text_ignores_ambiguous_abbreviations():
    # "MP" here is Member of Parliament, "AP" is Associated Press – neither is a state.
    assert extract_states("MP raises AI question in Lok Sabha, says AP report") == []


def test_extract_states_basic_and_order():
    got = [s for s, _ in extract_states("Karnataka and Tamil Nadu sign AI pact; Kerala watches")]
    assert got == ["Karnataka", "Tamil Nadu", "Kerala"]


def test_new_delhi_dateline_is_not_delhi_state():
    assert extract_states("New Delhi: Centre launches AI mission") == []
    assert [s for s, _ in extract_states("Delhi government approves AI policy")] == ["Delhi"]
    assert [s for s, _ in extract_states("Delhi's AI plan")] == ["Delhi"]


def test_extract_states_hyphenation_and_jk():
    assert [s for s, _ in extract_states("Uttar-Pradesh unveils AI mission")] == ["Uttar Pradesh"]
    assert [s for s, _ in extract_states("J&K plans AI lab")] == ["Jammu and Kashmir"]
    assert [s for s, _ in extract_states("Jammu and Kashmir plans AI lab")] == ["Jammu and Kashmir"]


def test_extract_cities_and_aliases():
    assert extract_cities("Bangalore-based startup, Hyderabad lab") == [("Bengaluru", "Karnataka"), ("Hyderabad", "Telangana")] \
        or {c for c, _ in extract_cities("Bangalore-based startup, Hyderabad lab")} == {"Bengaluru", "Hyderabad"}


def test_extract_institutions():
    names = {i.name for i in extract_institutions("IIT-Madras and IISc partner; IIT Delhi too")}
    assert names == {"IIT Madras", "IISc Bengaluru", "IIT Delhi"}
    assert extract_institutions("the iit entrance exam") == []


def test_dates_full_and_feed():
    assert normalize_date("Tue, 22 Sep 2026 07:00:00 GMT", TODAY).iso == "2026-09-22"
    r = normalize_date("2025-03-05T10:00:00Z", TODAY); assert (r.iso, r.precision) == ("2025-03-05", "day")
    assert normalize_date("5 March 2025", TODAY).iso == "2025-03-05"
    assert normalize_date("March 5, 2025", TODAY).iso == "2025-03-05"
    assert normalize_date("05/03/2025", TODAY).iso == "2025-03-05"   # day-first


def test_dates_partial_precision():
    r = normalize_date("March 2025", TODAY); assert (r.iso, r.precision) == ("2025-03-01", "month")
    r = normalize_date("2025", TODAY); assert (r.iso, r.precision) == ("2025-01-01", "year")


@pytest.mark.parametrize("raw", ["early 2025", "Q3 2025", "circa 2024", "soon", "31 Feb 2025", "", None])
def test_dates_never_invented(raw):
    r = normalize_date(raw, TODAY)
    assert r.iso is None and r.precision == "unknown" and r.note


def test_future_dates_rejected():
    r = normalize_date("2027-01-01", TODAY)
    assert r.iso is None and "future" in r.note


def test_trailing_state_word_stripped():
    assert normalize_state("Maharashtra State").state == "Maharashtra"
    assert normalize_state("Kerala Government").state == "Kerala"
