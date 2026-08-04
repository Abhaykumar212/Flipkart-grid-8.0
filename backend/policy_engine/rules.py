from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from backend import config
from backend.domain.causes import RootCause
from backend.domain.interventions import (
    MARGIN_SPENDING,
    InterventionDefinition,
    InterventionId,
)
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.contracts import CauseResult
from backend.session_state.state import SessionState

from .browsing import assist_permitted, permits as browsing_permits
from .reasons import PolicyReason, REQUIREMENT_REASONS


@dataclass(frozen=True, slots=True)
class RuleVerdict:
    reason: PolicyReason | None = None

    @property
    def rejected(self) -> bool:
        return self.reason is not None


Rule = Callable[
    [InterventionDefinition, SessionState, dict[str, float], RiskPrediction, CauseResult, datetime],
    RuleVerdict,
]


def _pass() -> RuleVerdict:
    return RuleVerdict()


def _protected(candidate: InterventionDefinition) -> bool:
    return candidate.intervention_id == InterventionId.NO_ACTION


def order_completed(candidate, state, _features, _risk, _causes, _now) -> RuleVerdict:
    if state.order_completed and not _protected(candidate):
        return RuleVerdict(PolicyReason.ORDER_ALREADY_COMPLETED)
    return _pass()


def risk_floor(candidate, _state, features, risk, _causes, _now) -> RuleVerdict:
    if risk.probability >= config.RISK_INTERVENTION_THRESHOLD or _protected(candidate):
        return _pass()
    # A deliberating shopper with an empty cart scores below the floor by
    # construction — the risk model won't extrapolate past a cart it can't see.
    # They can still be answered, but only with something free and quiet.
    if assist_permitted(features) and browsing_permits(candidate):
        return _pass()
    return RuleVerdict(PolicyReason.RISK_BELOW_INTERVENTION_THRESHOLD)


def session_cap(candidate, _state, features, _risk, _causes, _now) -> RuleVerdict:
    if (
        features["i_shown_count"] >= config.MAX_INTERVENTIONS_PER_SESSION
        and not _protected(candidate)
    ):
        return RuleVerdict(PolicyReason.SESSION_INTERVENTION_CAP_REACHED)
    return _pass()


def fatigue(candidate, _state, features, _risk, _causes, _now) -> RuleVerdict:
    if features["i_dismissal_count"] >= config.MAX_DISMISSALS and not _protected(candidate):
        return RuleVerdict(PolicyReason.REPEATED_DISMISSALS)
    return _pass()


def cooldown(candidate, state, _features, _risk, _causes, now) -> RuleVerdict:
    if _protected(candidate):
        return _pass()
    raw_expiry = state.cooldowns.get(candidate.intervention_id.value)
    if not raw_expiry:
        return _pass()
    try:
        expiry = datetime.fromisoformat(raw_expiry.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
    except ValueError:
        return _pass()
    if now < expiry:
        return RuleVerdict(PolicyReason.COOLDOWN_ACTIVE)
    return _pass()


def _requirement_met(name: str, features: dict[str, float]) -> bool:
    explicit_feature = {
        "review_summary_available": "review_summary_available",
        "delivery_data_available": "delivery_data_available",
        "price_history_available": "price_history_available",
        "discount_budget_available": "discount_budget_available",
    }.get(name)
    if explicit_feature in features:
        return features[explicit_feature] > 0
    if name.endswith("comparable_products") and "comparable_products_available" in features:
        return features["comparable_products_available"] >= 2
    if name.endswith("similar_in_stock") and "similar_products_in_stock" in features:
        return features["similar_products_in_stock"] >= 3
    checks = {
        "review_summary_available": features.get("review_summary_available", 0.0) > 0,
        "≥2_comparable_products": features["s_distinct_products_viewed"] >= 2,
        "delivery_data_available": (
            features["d_check_count"] > 0 or features["c_item_count"] > 0
        ),
        "price_history_available": features["c_item_count"] > 0,
        "≥3_similar_in_stock": features["s_distinct_products_viewed"] >= 3,
        "emi_eligible": features["pay_emi_eligible"] > 0,
        "payment_failure_occurred": features["pay_failure_count"] > 0,
        "checkout_started": features["s_checkout_start_count"] > 0,
        "discount_budget_available": features.get("discount_budget_available", 1.0) > 0,
        "cart_value≥5000": features["c_value"] >= config.EMI_MIN_CART_VALUE,
        "cart_value≥1000": features["c_value"] >= config.DISCOUNT_MIN_CART_VALUE,
        # Scarcity is only honest when the stock signal is real, so this gates
        # on the catalogue reading rather than on anything inferred.
        "low_stock_confirmed": features["p_any_low_stock"] > 0,
        "delivery_fee_present": features["d_fee"] > 0,
        "guest_session": features["u_is_new_user"] > 0,
    }
    return checks.get(name, False)


def requirements(candidate, _state, features, _risk, _causes, _now) -> RuleVerdict:
    for requirement in candidate.requires:
        if not _requirement_met(requirement, features):
            return RuleVerdict(REQUIREMENT_REASONS[requirement])
    return _pass()


def emi_floor(candidate, _state, features, _risk, _causes, _now) -> RuleVerdict:
    if (
        candidate.intervention_id == InterventionId.EMI_SUGGESTION
        and features["c_value"] < config.EMI_MIN_CART_VALUE
    ):
        return RuleVerdict(PolicyReason.CART_VALUE_BELOW_EMI_THRESHOLD)
    return _pass()


def coupon_conflict(candidate, _state, features, _risk, _causes, _now) -> RuleVerdict:
    if (
        candidate.intervention_id == InterventionId.LIMITED_TIME_DISCOUNT
        and features["c_promo_applied"] > 0
    ):
        return RuleVerdict(PolicyReason.EQUIVALENT_COUPON_ALREADY_APPLIED)
    return _pass()


def delivery_data(candidate, _state, features, _risk, _causes, _now) -> RuleVerdict:
    if (
        candidate.intervention_id == InterventionId.DELIVERY_REASSURANCE
        and features["d_check_count"] <= 0
        and features["c_item_count"] <= 0
    ):
        return RuleVerdict(PolicyReason.DELIVERY_DATA_UNAVAILABLE)
    return _pass()


def review_grounding(candidate, _state, features, _risk, _causes, _now) -> RuleVerdict:
    if (
        candidate.intervention_id == InterventionId.REVIEW_SUMMARY
        and features.get("review_summary_available", 0.0) <= 0
    ):
        return RuleVerdict(PolicyReason.NO_GROUNDED_SUMMARY_AVAILABLE)
    return _pass()


def discount_protection(candidate, _state, features, risk, causes, _now) -> RuleVerdict:
    """Every margin-spending lever clears the same bar, not just the discount.

    A waived delivery fee costs real money too. Gating only the headline
    discount would let the ranker spend margin through the side door whenever
    a delivery lever happened to outrank it.
    """
    if candidate.intervention_id not in MARGIN_SPENDING:
        return _pass()
    if risk.probability < config.RISK_HIGH_THRESHOLD:
        return RuleVerdict(PolicyReason.DISCOUNT_RISK_BELOW_HIGH_THRESHOLD)
    # Each margin lever answers a different friction, so each is verified
    # against the cause that would actually justify the spend.
    justifying = (
        RootCause.DELIVERY_CONCERN
        if candidate.intervention_id in (
            InterventionId.FREE_DELIVERY_WAIVER,
            InterventionId.DELIVERY_SPEED_UPGRADE,
        )
        else RootCause.PRICE_SENSITIVITY
    )
    if causes.probability_for(justifying) < config.DISCOUNT_MIN_PRICE_SENSITIVITY:
        return RuleVerdict(PolicyReason.PRICE_SENSITIVITY_NOT_VERIFIED)
    if features["c_value"] < config.DISCOUNT_MIN_CART_VALUE:
        return RuleVerdict(PolicyReason.CART_VALUE_BELOW_DISCOUNT_THRESHOLD)
    return _pass()


ORDERED_RULES: tuple[tuple[str, Rule], ...] = (
    ("order_completed", order_completed),
    ("risk_floor", risk_floor),
    ("session_cap", session_cap),
    ("fatigue", fatigue),
    ("cooldown", cooldown),
    ("requirements", requirements),
    ("emi_floor", emi_floor),
    ("coupon_conflict", coupon_conflict),
    ("delivery_data", delivery_data),
    ("review_grounding", review_grounding),
    ("discount_protection", discount_protection),
)
