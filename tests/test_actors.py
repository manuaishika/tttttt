from src.actors import identify_actors, is_national_actor


def classes(t, has_state=True):
    return [(a.name, a.actor_class, a.level) for a in identify_actors(t, has_state)]


def test_regulator_identity_from_registry():
    c = classes("TRAI Proposes Mandatory AI Policy and Incident Reporting", has_state=False)
    assert ("Telecom Regulatory Authority of India", "regulator_statutory_authority", "union") in c


def test_judiciary_state_and_union():
    assert ("High Court", "judiciary", "state") in classes("Gujarat HC releases AI policy barring use in court decisions")
    assert ("Supreme Court of India", "judiciary", "union") in classes("Supreme Court dismisses plea on AI regulation", False)


def test_state_government_cue_needs_state_anchor():
    assert ("State government", "state_government", "state") in classes("Kerala cabinet approves AI mission")
    assert all(c[1] != "state_government" for c in classes("Cabinet approves AI mission", has_state=False))


def test_union_government_generic_and_national_flag():
    acts = identify_actors("Centre to set up AI safety institute", has_state=False)
    assert acts[0].actor_class == "union_government" and is_national_actor(acts)


def test_no_actor_is_unknown_not_guessed():
    assert identify_actors("Vibe coding is the next big thing", True) == []


def test_acronym_case_sensitivity():
    # 'sc' inside words or lower-case must not become the Supreme Court
    assert all(a.name != "Supreme Court of India" for a in identify_actors("AI-based school scheme in Goa"))


def test_institution_registry_actor_has_location():
    a = [x for x in identify_actors("IIT Madras launches AI centre") if x.name == "IIT Madras"][0]
    assert (a.actor_class, a.state, a.website) == ("academic_research_institution", "Tamil Nadu", "https://www.iitm.ac.in")


def test_centre_of_excellence_is_not_the_union_government():
    for t in ["E-city set to host Rs 20-cr AI Centre of Excellence", "IT Park Phase-2 to house AI Centre of Excellence",
              "Inside CtrlS's 4.4 GW bet on India's AI and data centre boom"]:
        assert all(a.actor_class != "union_government" for a in identify_actors(t, has_state=False)), t
    for t in ["Centre to set up AI safety institute", "786 candidates trained in AI under FutureSkills PRIME: Centre",
              "Centre's AI advisory on deepfakes", "Union Cabinet approves IndiaAI Mission"]:
        assert any(a.actor_class == "union_government" for a in identify_actors(t, has_state=False)), t
