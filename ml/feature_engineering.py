"""Shared feature engineering for Phase 1 cart abandonment model.

This module is imported by both train_model.py and backend/main.py so that
training and inference use identical transformations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RAW_FEATURE_NAMES = [
    "cart_dwell_time_seconds",
    "cart_pdp_bounce_count",
    "reviews_expanded_count",
    "idle_time_before_checkout",
    "delivery_pincode_checked",
    "cart_value_to_aov_ratio",
    "delivery_fee_percentage",
    "est_delivery_days",
    "has_price_dropped_recently",
    "hist_abandonment_rate",
    "discount_sensitivity_score",
    "past_return_rate",
    "wishlist_item_count",
    "payment_method_saved",
]

ENGINEERED_FEATURE_NAMES = [
    # Continuous interaction features
    "price_shock_interaction",
    "bounce_review_interaction",
    "checkout_friction",
    "delivery_anxiety",
    "dwell_per_bounce",
    "value_sensitivity",
    "abandonment_momentum",
    "delivery_cost_burden",
    # Binary threshold features (matching data-generating process signals)
    "price_shock_flag",
    "quality_uncertainty_flag",
    "long_delivery_flag",
    "saved_payment_low_value_flag",
    # Additional derived features
    "dwell_centered",
    "high_hist_abandonment",
    "total_friction_score",
    "engagement_depth",
]

ALL_FEATURE_NAMES = RAW_FEATURE_NAMES + ENGINEERED_FEATURE_NAMES


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add interaction and derived features to a DataFrame of raw features.

    Accepts a DataFrame containing the 14 raw features and returns a new
    DataFrame with the raw features plus engineered interaction columns.
    The column order matches ALL_FEATURE_NAMES exactly.
    """
    result = df[RAW_FEATURE_NAMES].copy()

    # --- Continuous interaction features ---

    # High cart value + high delivery fee = price shock (strong abandon signal)
    result["price_shock_interaction"] = (
        result["cart_value_to_aov_ratio"] * result["delivery_fee_percentage"]
    )

    # Many bounces + many review reads = product uncertainty
    result["bounce_review_interaction"] = (
        result["cart_pdp_bounce_count"] * result["reviews_expanded_count"]
    )

    # Long idle + no saved payment = checkout friction
    result["checkout_friction"] = (
        result["idle_time_before_checkout"] * (1.0 - result["payment_method_saved"])
    )

    # Long delivery + pincode checking = delivery anxiety
    result["delivery_anxiety"] = (
        result["est_delivery_days"] * result["delivery_pincode_checked"]
    )

    # Time spent per bounce — low values indicate rapid comparison shopping
    result["dwell_per_bounce"] = (
        result["cart_dwell_time_seconds"] / (result["cart_pdp_bounce_count"] + 1.0)
    )

    # Expensive cart + discount sensitive shopper = high value sensitivity
    result["value_sensitivity"] = (
        result["cart_value_to_aov_ratio"] * result["discount_sensitivity_score"]
    )

    # Historical abandon rate + high return rate = momentum toward abandonment
    result["abandonment_momentum"] = (
        result["hist_abandonment_rate"] * (1.0 + result["past_return_rate"])
    )

    # Delivery fee as fraction of AOV ratio — how burdensome delivery feels
    result["delivery_cost_burden"] = (
        result["delivery_fee_percentage"] * result["est_delivery_days"]
    )

    # --- Binary threshold flags (mirror data-generating signal terms) ---

    # Price shock: high value cart AND high delivery fee
    result["price_shock_flag"] = (
        (result["cart_value_to_aov_ratio"] > 1.8)
        & (result["delivery_fee_percentage"] > 5.0)
    ).astype(np.float64)

    # Quality uncertainty: excessive bouncing AND review reading
    result["quality_uncertainty_flag"] = (
        (result["cart_pdp_bounce_count"] > 3)
        & (result["reviews_expanded_count"] > 2)
    ).astype(np.float64)

    # Long delivery: estimated delivery beyond 5 days
    result["long_delivery_flag"] = (
        result["est_delivery_days"] > 5
    ).astype(np.float64)

    # Saved payment + low value: payment saved but cart value below AOV
    result["saved_payment_low_value_flag"] = (
        (result["payment_method_saved"] == 1)
        & (result["cart_value_to_aov_ratio"] < 1.0)
    ).astype(np.float64)

    # --- Additional derived features ---

    # Centered dwell time (matches signal term: dwell - 180)
    result["dwell_centered"] = result["cart_dwell_time_seconds"] - 180.0

    # High historical abandonment rate (above median)
    result["high_hist_abandonment"] = (
        result["hist_abandonment_rate"] > 0.5
    ).astype(np.float64)

    # Total friction score: combines multiple friction signals
    result["total_friction_score"] = (
        result["idle_time_before_checkout"] / 300.0
        + result["delivery_fee_percentage"] / 15.0
        + (result["est_delivery_days"] - 1) / 9.0
        + (1.0 - result["payment_method_saved"])
    )

    # Engagement depth: browsing intensity indicator
    result["engagement_depth"] = (
        result["cart_pdp_bounce_count"]
        + result["reviews_expanded_count"]
        + result["delivery_pincode_checked"]
        + result["wishlist_item_count"]
    ).astype(np.float64)

    return result[ALL_FEATURE_NAMES]
