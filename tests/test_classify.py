import pytest
from src.classify import (classify, is_ai_related, screen, screen_after_classification, state_is_subject,
                          detect_opportunity)


@pytest.mark.parametrize("t,cat", [
    ("Kerala cabinet approves AI mission to boost governance", "policy_governance"),
    ("Chhattisgarh Cabinet approves Rs 500-crore AI Mission", "policy_governance"),
    ("Telangana signs MoU with Microsoft for AI skilling of 1 lakh students", "partnerships_investment"),
    ("IIT Madras launches AI centre of excellence for healthcare", "research_institutions"),
    ("Karnataka to use AI for crop disease detection, farmers to benefit", "deployment"),
    ("Gujarat HC releases AI policy barring use in court decisions", "policy_governance"),
    ("Kerala unveils AI-led governance overhaul to streamline administration", "deployment"),
    ("Gujarat, Meta join hands to launch WhatsApp chatbot for government services", "partnerships_investment"),
    ("State issues responsible AI guidelines for departments", "safety_responsible_ai"),
])
def test_category_examples(t, cat):
    assert classify(t).category == cat


def test_air_india_is_not_ai():
    assert not is_ai_related("Air India AI171 crash: Kerala families await report")
    assert not is_ai_related("Air India Express flight AI-1234 delayed")
    assert is_ai_related("Kerala sets up AI mission")


def test_opportunity_needs_type_and_forward_cue():
    assert classify("Applications open for AI governance fellowship at IIT Delhi").record_type == "opportunity"
    assert classify("IndiaAI Fellowship 2026-27: Get up to Rs 2 Lakh, check eligibility").record_type == "opportunity"
    assert classify("IIT Mandi opens applications for one-month residential program in AI").record_type == "opportunity"
    # a past event is an activity, an award is not an opening
    assert classify("IIT Bombay organised a workshop on AI ethics last week").record_type == "activity"
    assert classify("Researcher bags AI fellowship for work on bias").record_type == "activity"


def test_deadline_only_when_stated():
    assert detect_opportunity("Applications open for AI fellowship; last date 15 December 2026")[1] == "2026-12-15"
    assert detect_opportunity("Applications open for AI fellowship")[1] is None


def test_screen_reasons():
    assert screen("Opinion: AI will change Kerala", "")[1] == "opinion_or_commentary"
    assert screen("Monsoon forecast for Kerala", "")[1] == "not_ai_related"


def test_crime_and_market_excluded_but_policy_kept():
    t = "Man arrested for AI deepfake scam in Pune"
    assert screen_after_classification(t, "", classify(t))[0] is False
    t = "Telangana signs MoU with Microsoft for AI skilling"
    assert screen_after_classification(t, "", classify(t), state_subject=state_is_subject(t, "Telangana"))[0]


def test_investment_in_state_ai_infra_in_scope_but_startup_funding_not():
    t = "Google lays foundation for Rs 1.35 lakh crore AI hub in Visakhapatnam"
    assert screen_after_classification(t, "", classify(t))[0]
    t = "Hyderabad startup raises $10 million for AI chatbots"
    assert not screen_after_classification(t, "", classify(t))[0]


def test_deadline_without_year_resolved_against_publication_date():
    from datetime import date
    t = "Anthropic opens AI Safety Fellowship, apply by April 26"
    assert detect_opportunity(t, date(2026, 4, 1))[1] == "2026-04-26"
    assert detect_opportunity(t, date(2026, 5, 1))[1] == "2027-04-26"   # next occurrence on/after pub date
    assert detect_opportunity(t, None)[1] is None                        # no reference date -> do not guess


def test_loose_cues_do_not_make_an_opportunity():
    assert classify("Rajasthan's successful application of AI in governance makes waves at conference in Seoul").record_type == "activity"
    assert classify("Himachal plans MBBS internship stipend hike, AI push in medical education").record_type == "activity"
