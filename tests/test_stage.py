import pytest
from src.stage import stage_cue


@pytest.mark.parametrize("t,stage", [
    ("Chhattisgarh Cabinet approves Rs 500-crore AI Mission", "announced_or_approved"),
    ("Telangana signs MoU with Microsoft to train 1 lakh students in AI", "announced_or_approved"),
    ("Goa unveils AI policy to diversify economy beyond tourism", "announced_or_approved"),
    ("Karnataka to use AI for crop disease detection", "proposed_or_planned"),
    ("Goa to enforce AI traffic cameras from Jul 15", "proposed_or_planned"),
    ("Odisha plans to deploy AI in hospitals", "proposed_or_planned"),
    ("In Final Stage, Under Review: Goa IT Minister On Delayed AI Policy", "proposed_or_planned"),
    ("Telangana Transport Department Rolls Out AI Cameras to Curb Road Accidents", "implemented_or_operational"),
    ("Gautam Adani Inaugurates AI Centre of Excellence in Baramati", "implemented_or_operational"),
    ("Punjab police using AI to trace stolen vehicles", "implemented_or_operational"),
    ("Kerala's K-AI Initiative: AI for Governance", "unclear"),
])
def test_stage_cue_examples(t, stage):
    assert stage_cue(t) == stage


def test_empty_headline_is_unclear():
    assert stage_cue("") == "unclear"


@pytest.mark.parametrize("t,stage", [
    ("Punjab and Haryana High Court bars judicial officers from using AI tools to write judgments", "announced_or_approved"),
    ("Chhattisgarh Okays Artificial Intelligence Mission, To Spend Rs 500 Crore Over 5 Years", "announced_or_approved"),
    ("Telangana govt, AWS partner to train one lakh students in AI", "announced_or_approved"),
])
def test_rulings_approvals_and_partnerships_are_announcements(t, stage):
    assert stage_cue(t) == stage


def test_acronym_aim_is_not_the_verb_aims():
    assert stage_cue("Kerala's K-AI Initiative: AI For Governance Under Kerala Artificial Intelligence Mission (K-AIM)") == "unclear"
    assert stage_cue("Odisha aims to become an AI hub") == "proposed_or_planned"


from src.stage import activity_stage


def test_activity_stage_requires_strong_evidence():
    assert activity_stage("Cabinet approves AI mission", "single_secondary_source", 1)[0] == "undetermined"
    assert activity_stage("Cabinet approves AI mission", "primary_source", 1)[:2] == ("approved_constituted", "medium")
    assert activity_stage("Cabinet approves AI mission", "corroborated", 3)[:2] == ("approved_constituted", "low")


def test_activity_stage_never_infers_implementation_from_announcement():
    assert activity_stage("State launches AI policy", "primary_source", 1)[0] == "proposed_announced"
    assert activity_stage("State plans to deploy AI cameras", "corroborated", 2)[0] == "proposed_announced"
    assert activity_stage("Police AI cameras go live across city", "corroborated", 2)[0] == "undetermined"  # 'go live' != stated past


def test_manual_evidence_overrides():
    s = activity_stage("x", "unverified", 1, {"activity_stage": "under_implementation", "evidence": "tender notice"})
    assert s[:2] == ("under_implementation", "high")


def test_hyphenated_adjective_is_not_an_approval():
    assert activity_stage("TRAI proposes board-approved AI policies for telcos", "corroborated", 3)[0] == "proposed_announced"
