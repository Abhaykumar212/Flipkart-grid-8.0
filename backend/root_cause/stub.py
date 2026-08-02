from __future__ import annotations

from time import perf_counter

from backend import config
from backend.domain.causes import RootCause

from .contracts import CausePrediction, CauseResult
from .evidence import evidence_for


MODEL_VERSION = "cause-stub-v1"
THRESHOLDS: dict[RootCause, float] = {
    RootCause.PRICE_SENSITIVITY: 0.42,
    RootCause.PRODUCT_QUALITY_UNCERTAINTY: 0.40,
    RootCause.CHOICE_OVERLOAD: 0.38,
    RootCause.DELIVERY_CONCERN: 0.44,
    RootCause.AFFORDABILITY_OR_EMI_NEED: 0.36,
    RootCause.CHECKOUT_OR_PAYMENT_FAILURE: 0.48,
    RootCause.PRODUCT_AVAILABILITY_CONCERN: 0.34,
    RootCause.LOW_PURCHASE_INTENT: 0.40,
    RootCause.TRUST_OR_RETURN_POLICY_CONCERN: 0.32,
    RootCause.SESSION_INTERRUPTION_OR_DISTRACTION: 0.36,
}


def _ratio(value: float, ceiling: float) -> float:
    return min(1.0, max(0.0, value / ceiling))


def _probabilities(features: dict[str, float]) -> dict[RootCause, float]:
    cart_present = features["c_item_count"] > 0
    return {
        RootCause.PRICE_SENSITIVITY: 0.05
        + 0.18 * _ratio(features["s_price_sort_count"], 2)
        + 0.20 * _ratio(features["s_coupon_search_count"], 2)
        + 0.12 * _ratio(features["c_value_to_aov_ratio"], 3)
        + 0.10 * features["u_discount_usage_rate"],
        RootCause.PRODUCT_QUALITY_UNCERTAINTY: 0.08
        + 0.28 * _ratio(features["s_review_open_count"], 3)
        + 0.23 * _ratio(features["s_similar_product_view_count"], 5)
        + 0.12 * _ratio(features["s_review_dwell_seconds"], 120)
        + 0.08 * _ratio(4.2 - features["p_avg_rating"], 3.2),
        RootCause.CHOICE_OVERLOAD: 0.05
        + 0.32 * _ratio(features["s_comparison_count"], 2)
        + 0.22 * _ratio(features["s_distinct_products_viewed"], 6)
        + 0.18 * _ratio(features["s_cart_product_switch_count"], 4),
        RootCause.DELIVERY_CONCERN: 0.08
        + 0.38 * _ratio(features["d_check_count"], 3)
        + 0.20 * _ratio(features["d_max_days"] - 3, 7)
        + 0.15 * _ratio(features["d_fee_pct_of_cart"], 10),
        RootCause.AFFORDABILITY_OR_EMI_NEED: 0.05
        + 0.28 * _ratio(features["c_value_to_aov_ratio"], 3)
        + 0.18 * float(features["c_value"] >= config.EMI_MIN_CART_VALUE)
        + 0.10 * features["pay_emi_eligible"],
        RootCause.CHECKOUT_OR_PAYMENT_FAILURE: 0.05
        + 0.66 * _ratio(features["pay_failure_count"], 1)
        + 0.18 * _ratio(features["pay_method_change_count"], 1)
        + 0.08 * _ratio(features["s_checkout_start_count"], 1),
        RootCause.PRODUCT_AVAILABILITY_CONCERN: 0.05
        + 0.55 * features["p_any_out_of_stock"]
        + 0.25 * features["p_any_low_stock"],
        RootCause.LOW_PURCHASE_INTENT: 0.05
        + (0.28 * _ratio(features["s_idle_seconds_current"], 180) if cart_present else 0)
        + (0.18 * (1 - _ratio(features["s_event_velocity_per_min"], 8)) if cart_present else 0)
        + (0.10 * float(features["s_product_view_count"] <= 1) if cart_present else 0),
        RootCause.TRUST_OR_RETURN_POLICY_CONCERN: 0.05
        + 0.14 * features["u_is_new_user"]
        + 0.22 * _ratio(features["u_return_rate"], 0.5)
        + 0.12 * float(0 < features["p_min_rating_count"] < 100),
        RootCause.SESSION_INTERRUPTION_OR_DISTRACTION: 0.05
        + (0.28 * _ratio(features["s_idle_seconds_current"], 180) if cart_present else 0)
        + 0.10 * features["x_is_mobile"]
        + 0.12 * features["x_is_late_night"]
        + (0.12 * (1 - _ratio(features["s_event_velocity_per_min"], 8)) if cart_present else 0),
    }


def predict(features: dict[str, float]) -> CauseResult:
    """Deterministic threshold rules behind the Phase 9-compatible contract."""

    started = perf_counter()
    probabilities = {
        cause: round(min(0.95, max(0.0, value)), 6)
        for cause, value in _probabilities(features).items()
    }
    confidence = max(probabilities.values(), default=0.0)
    if confidence < config.UNKNOWN_CAUSE_THRESHOLD:
        return CauseResult.unknown(
            confidence,
            latency_ms=round((perf_counter() - started) * 1_000, 3),
        )
    predictions = tuple(
        CausePrediction(cause, probability, evidence_for(cause, features))
        for cause, probability in sorted(probabilities.items(), key=lambda item: item[0].value)
        if probability >= THRESHOLDS[cause]
    )
    if not predictions:
        return CauseResult.unknown(
            confidence,
            latency_ms=round((perf_counter() - started) * 1_000, 3),
        )
    return CauseResult(
        root_causes=tuple(sorted(
            predictions,
            key=lambda item: (-item.probability, item.cause.value),
        )),
        model_version=MODEL_VERSION,
        abstained=False,
        confidence=confidence,
        latency_ms=round((perf_counter() - started) * 1_000, 3),
    )
