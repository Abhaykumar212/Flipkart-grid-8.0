from backend.domain.causes import RootCause
from backend.domain.enums import Decision, RiskBand
from backend.explainability.structured import build_explanation
from backend.feature_engine.schema import FEATURE_SCHEMA_V1
from backend.policy_engine.engine import evaluate_all
from backend.recommendation.candidates import generate_candidates
from backend.recommendation.ranker import score_all
from backend.risk_model.contracts import RiskFactor, RiskPrediction
from backend.root_cause.contracts import CausePrediction, CauseResult
from backend.session_state.state import SessionState


def test_structured_explanation_uses_only_supplied_feature_evidence():
    features = {item.name: float(item.default) for item in FEATURE_SCHEMA_V1}
    features.update({"s_review_open_count": 3, "s_similar_product_view_count": 5})
    risk = RiskPrediction(0.82, 0.64, RiskBand.HIGH, "risk-test", (
        RiskFactor("s_review_open_count", 3, 0.2),
        RiskFactor("s_similar_product_view_count", 5, 0.1),
    ), 1)
    causes = CauseResult((CausePrediction(
        RootCause.PRODUCT_QUALITY_UNCERTAINTY,
        0.71,
        ("s_review_open_count", "s_similar_product_view_count"),
    ),), "cause-test", False, 0.71, 1)
    state = SessionState(session_id="s1")
    candidates = generate_candidates(causes, features)
    policy = evaluate_all(candidates, state, features, risk, causes)
    ranked = score_all(tuple(result.candidate for result in policy if result.effective_candidate), features, risk, causes)
    selected = ranked[0]
    explanation = build_explanation(
        decision_id="d1", features=features, risk=risk, causes=causes,
        policy_results=policy, ranked=ranked, selected=selected,
        decision=Decision.INTERVENE,
    )
    assert explanation["decision_id"] == "d1"
    assert all(item["feature"] in features and item["value"] == features[item["feature"]] for item in explanation["observations"])
    assert explanation["inference"]["root_cause"] == RootCause.PRODUCT_QUALITY_UNCERTAINTY.value
    assert explanation["rendered_by"] == "template"
