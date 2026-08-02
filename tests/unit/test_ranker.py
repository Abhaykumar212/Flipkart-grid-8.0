from dataclasses import replace

from backend.domain.causes import RootCause
from backend.domain.enums import RiskBand
from backend.domain.interventions import InterventionId
from backend.feature_engine.schema import FEATURE_SCHEMA_V1
from backend.recommendation.catalogue import CATALOGUE_BY_ID
from backend.recommendation.ranker import score_all
from backend.policy_engine.engine import evaluate_all, finalize_discount_protection
from backend.domain.enums import PolicyStatus
from backend.session_state.state import SessionState
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.contracts import CausePrediction, CauseResult


def _features() -> dict[str, float]:
    result = {item.name: float(item.default) for item in FEATURE_SCHEMA_V1}
    result.update({"u_affinity_informational": 0.5, "u_affinity_incentive": 0.5})
    return result


def _risk(probability: float = 0.82) -> RiskPrediction:
    return RiskPrediction(probability, 0.64, RiskBand.HIGH, "risk-test", (), 0)


def _causes() -> CauseResult:
    return CauseResult((
        CausePrediction(
            RootCause.PRODUCT_QUALITY_UNCERTAINTY,
            0.71,
            ("s_review_open_count", "s_review_dwell_seconds", "s_similar_product_view_count"),
        ),
    ), "cause-test", False, 0.71, 0)


def test_utility_breakdown_sums_and_no_action_is_zero():
    ranked = score_all((
        CATALOGUE_BY_ID[InterventionId.REVIEW_SUMMARY],
        CATALOGUE_BY_ID[InterventionId.NO_ACTION],
    ), _features(), _risk(), _causes())
    for item in ranked:
        assert abs(sum(item.score_breakdown.values()) - item.score) <= 0.001
    assert next(item for item in ranked if item.candidate.intervention_id == InterventionId.NO_ACTION).score == 0


def test_ranking_is_deterministic_for_100_runs():
    candidates = (
        CATALOGUE_BY_ID[InterventionId.REVIEW_SUMMARY],
        CATALOGUE_BY_ID[InterventionId.NO_ACTION],
    )
    expected = [item.to_dict() for item in score_all(candidates, _features(), _risk(), _causes())]
    for _ in range(100):
        assert [item.to_dict() for item in score_all(candidates, _features(), _risk(), _causes())] == expected


def test_near_tie_prefers_lower_cost_then_intrusiveness_then_id():
    base = CATALOGUE_BY_ID[InterventionId.REVIEW_SUMMARY]
    price = replace(
        CATALOGUE_BY_ID[InterventionId.PRICE_DROP_ALERT],
        supported_causes=base.supported_causes,
        prior_uplift=base.prior_uplift,
    )
    ranked = score_all((base, price), _features(), _risk(), _causes())
    assert ranked[0].candidate.intervention_id == InterventionId.PRICE_DROP_ALERT
    assert ranked[0].tie_break_applied


def test_discount_is_downgraded_when_low_cost_action_is_within_point_one():
    features = _features()
    features.update({"c_value": 10_000, "c_item_count": 1})
    causes = CauseResult((CausePrediction(
        RootCause.PRICE_SENSITIVITY,
        0.8,
        ("s_price_sort_count", "s_coupon_search_count", "c_value_to_aov_ratio"),
    ),), "cause-test", False, 0.8, 0)
    candidates = (
        CATALOGUE_BY_ID[InterventionId.PRICE_DROP_ALERT],
        CATALOGUE_BY_ID[InterventionId.LIMITED_TIME_DISCOUNT],
        CATALOGUE_BY_ID[InterventionId.NO_ACTION],
    )
    policy = evaluate_all(candidates, SessionState(session_id="s1"), features, _risk(0.8), causes)
    ranked = score_all(candidates, features, _risk(0.8), causes)
    finalized = finalize_discount_protection(policy, ranked)
    discount = next(item for item in finalized if item.candidate.intervention_id == InterventionId.LIMITED_TIME_DISCOUNT)
    assert discount.status == PolicyStatus.DOWNGRADE
    assert discount.replacement is not None
    assert discount.replacement.intervention_id == InterventionId.PRICE_DROP_ALERT
