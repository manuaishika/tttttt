from datetime import date

from src.opportunity_extract import (extract_deadlines, extract_eligibility, extract_fees_stipend,
                                     extract_programme_dates)

PUB = date(2026, 11, 10)


def test_last_date_to_submit_applications_is_extracted_with_evidence():
    t = ("IIT Roorkee has invited applications for its six-week AI winter training programme. "
         "The last date to submit applications for both batches is November 29, 2026.")
    h = extract_deadlines(t, PUB)
    assert [x.iso for x in h] == ["2026-11-29"]
    assert h[0].confidence == "high" and "November 29, 2026" in h[0].excerpt


def test_publication_date_is_never_a_deadline():
    t = "Published on November 10, 2026. IIT Roorkee announced an AI winter school for students."
    assert extract_deadlines(t, PUB) == []


def test_programme_start_date_is_not_a_deadline():
    t = "The programme starts on December 1, 2026 and runs for six weeks."
    assert extract_deadlines(t, PUB) == []
    assert extract_programme_dates(t)


def test_deadline_and_start_in_same_text_are_separated():
    t = "Applications close on November 25, 2026. Classes will commence from December 2, 2026."
    assert [x.iso for x in extract_deadlines(t, PUB)] == ["2026-11-25"]
    assert any("December 2" in s for s in extract_programme_dates(t))


def test_cue_followed_by_programme_wording_is_rejected():
    t = "There is no deadline mentioned; the session will be held from 5 December 2026."
    assert extract_deadlines(t, PUB) == []


def test_genuinely_unstated_deadline_stays_unstated():
    assert extract_deadlines("Students can apply on the official website. Selected candidates get a stipend.", PUB) == []


def test_yearless_deadline_is_resolved_against_publication_and_marked_medium():
    h = extract_deadlines("Interested candidates can apply by April 26.", date(2026, 4, 16))
    assert [(x.iso, x.confidence) for x in h] == [("2026-04-26", "medium")]


def test_weak_cue_requires_application_context():
    assert extract_deadlines("The exhibition is open till December 10, 2026.", PUB) == []
    h = extract_deadlines("Registrations are open till December 10, 2026.", PUB)
    assert [(x.iso, x.confidence) for x in h] == [("2026-12-10", "low")]


def test_other_fields_carry_evidence():
    t = "The programme is open to B.Tech students. A monthly stipend of Rs 10,000 will be provided."
    assert extract_eligibility(t) and extract_fees_stipend(t)
