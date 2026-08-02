"""Shared feature engineering for the cart-abandonment model.

Imported by both `train_model.py` and `backend/main.py` so training and
inference apply byte-identical transformations.

Design note — why there are no hardcoded threshold flags here
-------------------------------------------------------------
An earlier version of this module contained indicator columns such as
`(cart_value_to_aov_ratio > 1.8) & (delivery_fee_percentage > 5.0)`. Those
constants were copied from the data generator's own hidden signal, which made
the feature set an answer key rather than a hypothesis: the reported score
partly measured our knowledge of the simulator, not the model's ability to
learn. It also had no production analogue — nobody can justify the number 1.8
to a reviewer.

Every engineered feature below is instead a **smooth, unit-free combination of
observable quantities**, expressing a domain hypothesis about how two frictions
compound. Where a threshold genuinely matters, the gradient-boosted trees find
it themselves from data — which is exactly what they are good at.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RAW_FEATURE_NAMES = [
    # A. Cart engagement
    "seconds_spent_in_cart",
    "times_returned_to_product_page",
    "product_reviews_read",
    "seconds_idle_before_checkout",
    "delivery_pincode_checks",
    "saved_items_in_wishlist",
    # B. Cost friction
    "cart_value_vs_typical_order",
    "delivery_fee_percent_of_cart",
    "price_dropped_since_first_view",
    "discount_seeking_tendency",
    "failed_coupon_attempts",
    # C. Delivery friction
    "estimated_delivery_days",
    # D. Checkout & trust friction
    "payment_method_on_file",
    "checkout_steps_completed",
    "payment_attempts_failed",
    "is_guest_checkout",
    # E. Customer history
    "past_abandonment_rate",
    "past_order_return_rate",
    "lifetime_orders_placed",
    "days_since_last_purchase",
    # F. Session context
    "is_mobile_session",
    "is_late_night_session",
]

ENGINEERED_FEATURE_NAMES = [
    "extra_cost_burden_score",
    "product_research_intensity",
    "checkout_friction_events",
    "delivery_concern_index",
    "dwell_per_return_visit",
    "hesitation_ratio",
    "price_sensitivity_exposure",
    "customer_loyalty_score",
    "checkout_progress_ratio",
    "trust_barrier_score",
]

ALL_FEATURE_NAMES = RAW_FEATURE_NAMES + ENGINEERED_FEATURE_NAMES

# One-line justification per engineered feature, for the presentation deck.
ENGINEERED_FEATURE_RATIONALE: dict[str, str] = {
    "extra_cost_burden_score": "Shipping fee and basket size compound: a 10% fee hurts far more on an unusually large cart. Captures the #1 documented abandonment driver as a single interaction.",
    "product_research_intensity": "Returning to the product page AND reading reviews together indicate an unresolved decision, which neither signal captures alone.",
    "checkout_friction_events": "Count of concrete blockers hit at checkout (failed payments, failed coupons, no saved card, guest flow). Directly actionable for Phase 2 interventions.",
    "delivery_concern_index": "Slow promised delivery matters much more when the shopper is actively re-checking their pincode.",
    "dwell_per_return_visit": "Time in cart normalised by visit count. Distinguishes one long considered session from rapid comparison-shopping loops.",
    "hesitation_ratio": "Share of cart time spent idle. A scale-free measure of hesitation that works for both short and long sessions.",
    "price_sensitivity_exposure": "A deal-seeking shopper facing an above-average basket is the classic discount-abandonment profile.",
    "customer_loyalty_score": "Purchase frequency damped by recency — a compact RFM summary. High-value loyal shoppers behave very differently.",
    "checkout_progress_ratio": "Fraction of the checkout funnel completed. The single clearest commitment signal available.",
    "trust_barrier_score": "Guest checkout combined with an above-average basket: spending significant money without an account relationship.",
}


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add domain-motivated interaction features to a frame of raw features.

    Accepts a DataFrame containing the raw features and returns a new DataFrame
    with raw + engineered columns, ordered exactly as ALL_FEATURE_NAMES.
    """
    result = df[RAW_FEATURE_NAMES].copy().astype(float)

    # --- B. Cost friction interactions ---

    # Fee burden scales with how large the basket is for this particular shopper.
    result["extra_cost_burden_score"] = (
        result["delivery_fee_percent_of_cart"] / 10.0
    ) * result["cart_value_vs_typical_order"]

    # Deal-seeker facing an above-average basket.
    result["price_sensitivity_exposure"] = (
        result["discount_seeking_tendency"] * result["cart_value_vs_typical_order"]
    )

    # --- A. Engagement interactions ---

    # Unresolved-decision signal: revisiting the product AND reading reviews.
    result["product_research_intensity"] = (
        result["times_returned_to_product_page"] * result["product_reviews_read"]
    )

    # Long single session vs. many short comparison loops.
    result["dwell_per_return_visit"] = result["seconds_spent_in_cart"] / (
        result["times_returned_to_product_page"] + 1.0
    )

    # Scale-free hesitation: what share of the cart session was idle?
    result["hesitation_ratio"] = result["seconds_idle_before_checkout"] / (
        result["seconds_spent_in_cart"] + 1.0
    )

    # --- C. Delivery interaction ---

    # Slow delivery matters more when they're actively checking serviceability.
    result["delivery_concern_index"] = (
        result["estimated_delivery_days"] * result["delivery_pincode_checks"]
    )

    # --- D. Checkout & trust ---

    # Concrete blockers encountered. Each addend is an event Phase 2 can act on.
    result["checkout_friction_events"] = (
        result["payment_attempts_failed"]
        + result["failed_coupon_attempts"]
        + (1.0 - result["payment_method_on_file"])
        + result["is_guest_checkout"]
    )

    # Funnel completion, normalised to [0, 1] over the 3-step checkout.
    result["checkout_progress_ratio"] = result["checkout_steps_completed"] / 3.0

    # Spending meaningfully without an account relationship.
    result["trust_barrier_score"] = (
        result["is_guest_checkout"] * result["cart_value_vs_typical_order"]
    )

    # --- E. Customer history ---

    # Compact RFM: frequency damped by recency (months since last purchase).
    result["customer_loyalty_score"] = result["lifetime_orders_placed"] / (
        1.0 + result["days_since_last_purchase"] / 30.0
    )

    return result[ALL_FEATURE_NAMES].astype(np.float64)
