"""Risk scoring on the 22-feature model, driven by the 67-feature session state.

Why this exists
---------------
The versioned model is trained on the causal simulator, whose abandon/convert
classes separate almost perfectly: its own reliability curve puts 4,211 holdout
sessions at p=0.999 against a 100% observed abandon rate. Faithful to its
training data, and nearly useless to look at — real sessions pile up at the
ceiling and the number stops moving.

The 22-feature model spreads the same scenarios across 5.9%-87.9%, and orders
them the way a human would: a shopper at checkout step 3 with a saved card
scores 5.9%, one idling over an oversized basket scores 87.9%.

So the session state stays the source of truth and this maps it down to the 22
inputs that model expects. The mapping is 1:1 for 21 of them, which is what
makes the SHAP attribution translatable back into the vocabulary the rest of
the product speaks.
"""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import joblib
import numpy as np
import pandas as pd

from backend import config
from backend.domain.enums import RiskBand

from .contracts import RiskFactor, RiskPrediction

ARTIFACT_DIR = Path(config.PROJECT_ROOT) / "ml" / "artifacts"

#: 22-feature model input -> the session feature that supplies it. The rest of
#: the product speaks the session vocabulary, so SHAP is reported back in it.
SOURCE: dict[str, str] = {
    "seconds_spent_in_cart": "c_age_seconds",
    "times_returned_to_product_page": "s_cart_product_switch_count",
    "product_reviews_read": "s_review_open_count",
    "seconds_idle_before_checkout": "s_idle_seconds_current",
    "delivery_pincode_checks": "d_check_count",
    "cart_value_vs_typical_order": "c_value_to_aov_ratio",
    "delivery_fee_percent_of_cart": "d_fee_pct_of_cart",
    "price_dropped_since_first_view": "c_max_price_drop_pct",
    "discount_seeking_tendency": "u_discount_usage_rate",
    "failed_coupon_attempts": "s_coupon_search_count",
    "estimated_delivery_days": "d_max_days",
    "payment_method_on_file": "pay_method_on_file",
    "checkout_steps_completed": "pay_checkout_max_step",
    "payment_attempts_failed": "pay_failure_count",
    "is_guest_checkout": "u_is_new_user",
    "past_abandonment_rate": "u_prior_abandonment_rate",
    "past_order_return_rate": "u_return_rate",
    "lifetime_orders_placed": "u_lifetime_orders",
    "days_since_last_purchase": "u_days_since_last_purchase",
    "is_mobile_session": "x_is_mobile",
    "is_late_night_session": "x_is_late_night",
    # No session counter feeds this one; the wishlist is client-side only.
    "saved_items_in_wishlist": "",
}

#: Ranges the model was trained over. Feeding it values it never saw is exactly
#: how the other model ended up pinned at the ceiling.
BOUNDS: dict[str, tuple[float, float]] = {
    "seconds_spent_in_cart": (0, 900),
    "times_returned_to_product_page": (0, 10),
    "product_reviews_read": (0, 8),
    "seconds_idle_before_checkout": (0, 300),
    "delivery_pincode_checks": (0, 5),
    "saved_items_in_wishlist": (0, 20),
    "cart_value_vs_typical_order": (0, 6),
    "delivery_fee_percent_of_cart": (0, 25),
    "price_dropped_since_first_view": (0, 1),
    "discount_seeking_tendency": (0, 1),
    "failed_coupon_attempts": (0, 5),
    "estimated_delivery_days": (1, 10),
    "payment_method_on_file": (0, 1),
    "checkout_steps_completed": (0, 3),
    "payment_attempts_failed": (0, 3),
    "is_guest_checkout": (0, 1),
    "past_abandonment_rate": (0, 1),
    "past_order_return_rate": (0, 1),
    "lifetime_orders_placed": (0, 50),
    "days_since_last_purchase": (0, 365),
    "is_mobile_session": (0, 1),
    "is_late_night_session": (0, 1),
}

_FLAGS = {"price_dropped_since_first_view", "payment_method_on_file", "is_guest_checkout",
          "is_mobile_session", "is_late_night_session"}

_model: Any = None
_explainer: Any = None
_calibrator: Any = None
_names: list[str] = []


class LegacyUnavailable(RuntimeError):
    """The 22-feature artifacts are missing; run scripts/train_all.ps1."""


def load() -> None:
    global _model, _explainer, _calibrator, _names
    if _model is not None:
        return
    required = [ARTIFACT_DIR / n for n in ("model.joblib", "explainer.joblib", "feature_names.json")]
    if not all(path.exists() for path in required):
        raise LegacyUnavailable(f"missing artifacts under {ARTIFACT_DIR}")
    _model = joblib.load(ARTIFACT_DIR / "model.joblib")
    _explainer = joblib.load(ARTIFACT_DIR / "explainer.joblib")
    calibrator_path = ARTIFACT_DIR / "calibrator.joblib"
    _calibrator = joblib.load(calibrator_path) if calibrator_path.exists() else None
    _names = json.loads((ARTIFACT_DIR / "feature_names.json").read_text(encoding="utf-8"))


def to_legacy_row(features: dict[str, float]) -> dict[str, float]:
    """Project the session vector onto the 22 inputs, clamped to training range."""
    row: dict[str, float] = {}
    for name, source in SOURCE.items():
        value = float(features.get(source, 0.0)) if source else 0.0
        if name == "price_dropped_since_first_view":
            value = 1.0 if value > 0 else 0.0
        low, high = BOUNDS[name]
        row[name] = float(min(max(value, low), high))
    return row


def _band(probability: float) -> RiskBand:
    if probability >= 0.75:
        return RiskBand.HIGH
    if probability >= 0.45:
        return RiskBand.MEDIUM
    return RiskBand.LOW


def _shap_row(frame: pd.DataFrame) -> np.ndarray:
    values = _explainer(frame)
    array = np.asarray(values.values, dtype=float)
    if array.ndim == 3:
        array = array[:, :, -1]
    return array[0]


def predict(features: dict[str, float]) -> RiskPrediction:
    """Score the session and report attribution in session-feature terms."""
    from ml.feature_engineering import RAW_FEATURE_NAMES, engineer_features

    started = perf_counter()
    load()
    row = to_legacy_row(features)
    frame = engineer_features(pd.DataFrame([row], columns=list(RAW_FEATURE_NAMES)))
    probability = float(_model.predict_proba(frame)[0, 1])
    if _calibrator is not None:
        probability = float(_calibrator.predict([probability])[0])

    shap_row = _shap_row(frame)
    by_legacy = dict(zip(_names, (float(v) for v in shap_row)))

    # Translate back into session-feature names. The 10 engineered inputs have
    # no session counterpart, so they stay out of the trail the UI narrates.
    shap_by_feature: dict[str, float] = {}
    for legacy_name, source in SOURCE.items():
        if source and legacy_name in by_legacy:
            shap_by_feature[source] = by_legacy[legacy_name]

    # Same contract as the versioned model: no cart, no abandonment to predict.
    scored = features.get("c_item_count", 0.0) > 0 and features.get("s_cart_add_count", 0.0) > 0
    if not scored:
        probability = min(probability, 0.12)

    ordered = sorted(shap_by_feature.items(), key=lambda item: abs(item[1]), reverse=True)[:5]
    factors = tuple(
        RiskFactor(name, float(features.get(name, 0.0)), value) for name, value in ordered
    )
    return RiskPrediction(
        float(np.clip(probability, 0, 1)),
        min(1.0, abs(probability - 0.5) * 2),
        _band(probability),
        "risk-legacy-v1",
        factors,
        (perf_counter() - started) * 1000,
        shap_by_feature=shap_by_feature,
        scored=scored,
    )
