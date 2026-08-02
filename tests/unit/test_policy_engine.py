from datetime import datetime, timedelta, timezone

from backend.domain.causes import RootCause
from backend.domain.enums import Channel, Decision, RiskBand
from backend.domain.interventions import InterventionId
from backend.feature_engine.schema import FEATURE_SCHEMA_V1
from backend.policy_engine.reasons import PolicyReason
from backend.policy_engine.rules import ORDERED_RULES
from backend.recommendation.catalogue import CATALOGUE_BY_ID
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.contracts import CausePrediction, CauseResult
from backend.session_state.state import SessionState
from backend.orchestrator.pipeline import _select
from backend.recommendation.ranker import ScoredIntervention


NOW = datetime(2026, 8, 2, 12, tzinfo=timezone.utc)


def _features() -> dict[str, float]:
    return {item.name: float(item.default) for item in FEATURE_SCHEMA_V1}


def _risk(probability: float = 0.8) -> RiskPrediction:
    return RiskPrediction(probability, 0.6, RiskBand.HIGH, "risk-test", (), 0)


def _causes(price: float = 0.7) -> CauseResult:
    return CauseResult((CausePrediction(RootCause.PRICE_SENSITIVITY, price, ("s_price_sort_count",)),), "cause-test", False, price, 0)


def _rule(name: str):
    return dict(ORDERED_RULES)[name]


def test_all_eleven_rules_are_frozen_in_order():
    assert [name for name, _ in ORDERED_RULES] == [
        "order_completed", "risk_floor", "session_cap", "fatigue", "cooldown",
        "requirements", "emi_floor", "coupon_conflict", "delivery_data",
        "review_grounding", "discount_protection",
    ]


def test_each_policy_rule_returns_its_documented_reason():
    state = SessionState(session_id="s1")
    features = _features()
    no_action = CATALOGUE_BY_ID[InterventionId.NO_ACTION]
    review = CATALOGUE_BY_ID[InterventionId.REVIEW_SUMMARY]
    emi = CATALOGUE_BY_ID[InterventionId.EMI_SUGGESTION]
    discount = CATALOGUE_BY_ID[InterventionId.LIMITED_TIME_DISCOUNT]
    delivery = CATALOGUE_BY_ID[InterventionId.DELIVERY_REASSURANCE]

    state.order_completed = True
    assert _rule("order_completed")(review, state, features, _risk(), _causes(), NOW).reason == PolicyReason.ORDER_ALREADY_COMPLETED
    state.order_completed = False
    assert _rule("risk_floor")(review, state, features, _risk(0.2), _causes(), NOW).reason == PolicyReason.RISK_BELOW_INTERVENTION_THRESHOLD
    features["i_shown_count"] = 3
    assert _rule("session_cap")(review, state, features, _risk(), _causes(), NOW).reason == PolicyReason.SESSION_INTERVENTION_CAP_REACHED
    features["i_shown_count"] = 0
    features["i_dismissal_count"] = 2
    assert _rule("fatigue")(review, state, features, _risk(), _causes(), NOW).reason == PolicyReason.REPEATED_DISMISSALS
    features["i_dismissal_count"] = 0
    state.cooldowns[review.intervention_id.value] = (NOW + timedelta(minutes=1)).isoformat()
    assert _rule("cooldown")(review, state, features, _risk(), _causes(), NOW).reason == PolicyReason.COOLDOWN_ACTIVE
    assert _rule("requirements")(emi, state, features, _risk(), _causes(), NOW).reason == PolicyReason.EMI_UNAVAILABLE
    features["pay_emi_eligible"] = 1
    assert _rule("emi_floor")(emi, state, features, _risk(), _causes(), NOW).reason == PolicyReason.CART_VALUE_BELOW_EMI_THRESHOLD
    features["c_promo_applied"] = 1
    assert _rule("coupon_conflict")(discount, state, features, _risk(), _causes(), NOW).reason == PolicyReason.EQUIVALENT_COUPON_ALREADY_APPLIED
    assert _rule("delivery_data")(delivery, state, features, _risk(), _causes(), NOW).reason == PolicyReason.DELIVERY_DATA_UNAVAILABLE
    features["review_summary_available"] = 0
    assert _rule("review_grounding")(review, state, features, _risk(), _causes(), NOW).reason == PolicyReason.NO_GROUNDED_SUMMARY_AVAILABLE
    assert _rule("discount_protection")(discount, state, features, _risk(0.6), _causes(), NOW).reason == PolicyReason.DISCOUNT_RISK_BELOW_HIGH_THRESHOLD
    assert _rule("risk_floor")(no_action, state, features, _risk(0.1), _causes(), NOW).reason is None


def _scored(intervention_id: InterventionId, confidence: float, score: float = 0.5) -> ScoredIntervention:
    candidate = CATALOGUE_BY_ID[intervention_id]
    channel = candidate.allowed_channels[0] if candidate.allowed_channels else None
    return ScoredIntervention(candidate, score, confidence, {}, channel, None, ())


def test_all_six_frozen_confidence_rows_have_safe_behavior():
    # Low/any is enforced before selection by the risk-floor policy.
    low_policy = _rule("risk_floor")(
        CATALOGUE_BY_ID[InterventionId.REVIEW_SUMMARY],
        SessionState(session_id="low"),
        _features(),
        _risk(0.2),
        _causes(),
        NOW,
    )
    assert low_policy.reason == PolicyReason.RISK_BELOW_INTERVENTION_THRESHOLD

    high_confidence = _causes(0.8)
    decision, selected = _select(
        (_scored(InterventionId.REVIEW_SUMMARY, 0.82),), high_confidence, _risk(0.8)
    )
    assert decision == Decision.INTERVENE and selected is not None

    # Medium recommendation confidence downgrades a costly top action to LOW.
    decision, selected = _select((
        _scored(InterventionId.LIMITED_TIME_DISCOUNT, 0.65, 0.6),
        _scored(InterventionId.PRICE_DROP_ALERT, 0.62, 0.4),
    ), high_confidence, _risk(0.8))
    assert decision == Decision.INTERVENE
    assert selected is not None and selected.candidate.cost_level.value == "LOW"

    unknown = CauseResult.unknown(0.3)
    decision, selected = _select(
        (_scored(InterventionId.WISHLIST_REMINDER, 0.3),), unknown, _risk(0.8)
    )
    assert decision == Decision.ABSTAIN and selected is None

    # Medium-risk/high-confidence uses the subtle inline LOW-cost result.
    inline = _scored(InterventionId.REVIEW_SUMMARY, 0.8)
    assert inline.channel == Channel.INLINE_CARD
    decision, selected = _select((inline,), high_confidence, _risk(0.6))
    assert decision == Decision.INTERVENE and selected == inline

    # The sixth row (low-confidence discount) is rejected by rule 11.
    verdict = _rule("discount_protection")(
        CATALOGUE_BY_ID[InterventionId.LIMITED_TIME_DISCOUNT],
        SessionState(session_id="discount"),
        {**_features(), "c_value": 2_000},
        _risk(0.8),
        _causes(0.3),
        NOW,
    )
    assert verdict.reason == PolicyReason.PRICE_SENSITIVITY_NOT_VERIFIED
