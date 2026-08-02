from __future__ import annotations

from time import perf_counter

from backend import config
from backend.domain.enums import RiskBand

from .contracts import RiskFactor, RiskPrediction


MODEL_VERSION = "risk-stub-v1"


def _bounded(value: float, ceiling: float) -> float:
    return min(1.0, max(0.0, value / ceiling))


def predict(features: dict[str, float]) -> RiskPrediction:
    """Transparent Phase 5 risk score; replaced behind this contract in Phase 8."""

    started = perf_counter()
    signals = {
        "s_review_open_count": 0.20 * _bounded(features["s_review_open_count"], 3),
        "s_similar_product_view_count": 0.20
        * _bounded(features["s_similar_product_view_count"], 5),
        "s_price_sort_count": 0.18 * _bounded(features["s_price_sort_count"], 2),
        "s_coupon_search_count": 0.18 * _bounded(features["s_coupon_search_count"], 2),
        "d_check_count": 0.24 * _bounded(features["d_check_count"], 3),
        "pay_failure_count": 0.34 * _bounded(features["pay_failure_count"], 1),
        "s_cart_view_count": 0.08 * _bounded(features["s_cart_view_count"], 3),
        "c_value_to_aov_ratio": 0.10 * _bounded(features["c_value_to_aov_ratio"], 3),
        "s_distinct_products_viewed": 0.08
        * _bounded(features["s_distinct_products_viewed"], 6),
        "s_idle_seconds_current": 0.08 * _bounded(features["s_idle_seconds_current"], 120),
        "pay_method_change_count": 0.10
        * _bounded(features["pay_method_change_count"], 1),
    }
    checkout_relief = 0.12 * _bounded(features["pay_checkout_max_step"], 3)
    probability = min(0.98, max(0.02, 0.12 + sum(signals.values()) - checkout_relief))
    if probability >= config.RISK_HIGH_THRESHOLD:
        band = RiskBand.HIGH
    elif probability >= config.RISK_INTERVENTION_THRESHOLD:
        band = RiskBand.MEDIUM
    else:
        band = RiskBand.LOW
    factors = tuple(
        RiskFactor(feature=name, value=features[name], shap=round(contribution, 6))
        for name, contribution in sorted(
            signals.items(), key=lambda item: (-abs(item[1]), item[0])
        )[:5]
    )
    return RiskPrediction(
        probability=round(probability, 6),
        confidence=round(abs(probability - 0.5) * 2, 6),
        band=band,
        model_version=MODEL_VERSION,
        top_factors=factors,
        latency_ms=round((perf_counter() - started) * 1_000, 3),
    )
