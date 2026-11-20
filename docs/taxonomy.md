# Taxonomy

Records are labelled with **one primary category** and **one sector**. Categories are the six from the project brief. Rules live in `src/classify.py` (keyword rules, v1) and are intentionally inspectable: every category decision can be traced to a pattern.

## Categories

| Key | Label | What counts | Typical examples |
|-----|-------|-------------|------------------|
| `policy_governance` | AI policy and governance | A state/UT government **announcing, approving or operating** an AI policy, mission, task force, regulatory framework or guideline | "State X cabinet approves AI Mission", "Y constitutes AI task force", "High Court releases AI-use policy" |
| `deployment` | AI deployment and public infrastructure | AI **used in** public services or infrastructure | AI crop advisories, AI TB screening in district hospitals, AI traffic/policing systems, AI in e-governance |
| `research_institutions` | AI research and institutional development | Creation or expansion of **research capacity**: centres of excellence, labs, institute programmes | "IIT X launches AI centre", "State sets up AI data/compute centre of excellence" |
| `partnerships_investment` | AI partnerships and investments | MoUs, government–industry/university collaborations, funding, budget lines, investment | "State signs MoU with Google for AI", "Budget earmarks ₹X crore for AI" |
| `safety_responsible_ai` | AI safety and responsible AI | Ethics, fairness, auditing, accountability, risk governance, safety research, deepfake *regulation* | "State issues responsible-AI guidelines", "AI ethics board formed" |
| `education_opportunities` | AI education and opportunities | AI in curricula and skilling; fellowships, internships, workshops, scholarships, conferences | "State to teach AI in schools", "AI fellowship applications open" |

## Sectors

`agriculture`, `healthcare`, `education`, `environment`, `defence`, `policing_justice`, `infrastructure`, `public_administration`, `none`.

Sector is independent of category: "AI TB-screening rollout" is `deployment` + `healthcare`; "State–Microsoft MoU on AI skilling for farmers" is `partnerships_investment` + `agriculture`.

## Two logical datasets

* **Activities** (`record_type = activity`): things that happened — policies, deployments, MoUs, institutional launches.
* **Opportunities** (`record_type = opportunity`): things a student/researcher can **apply to or attend** — fellowships, internships, scholarships, workshops, conferences, competitions. Detected by application-oriented cues ("applications open", "call for", "fellowship", "internship"...) and stored in a separate file with `opportunity_type` and `deadline` fields. Opportunities may be `Pan-India` when open to all states.

## Tie-breaking rules (so classification is reproducible)

1. Each category has weighted keyword patterns; the highest total wins.
2. If the top two are within a small margin, `category_confidence` is `low` and the precedence below breaks ties:
   `safety_responsible_ai` > `policy_governance` > `partnerships_investment` > `research_institutions` > `deployment` > `education_opportunities`.
   (More specific/rarer categories win over broader ones.)
3. A record matching **no** category rule is **excluded** (reason `no_category_match`) rather than dumped in an "other" bucket.

## What this taxonomy deliberately does not do

* It does not judge **quality** or **impact** of an activity.
* It does not infer activity from absence of news (see `docs/benchmark-framework.md` on evidence vs. absence).
