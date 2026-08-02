from enum import StrEnum


class PolicyReason(StrEnum):
    ORDER_ALREADY_COMPLETED = "order_already_completed"
    RISK_BELOW_INTERVENTION_THRESHOLD = "risk_below_intervention_threshold"
    SESSION_INTERVENTION_CAP_REACHED = "session_intervention_cap_reached"
    REPEATED_DISMISSALS = "repeated_dismissals"
    COOLDOWN_ACTIVE = "cooldown_active"
    REVIEW_SUMMARY_UNAVAILABLE = "requirement_not_met:review_summary_available"
    COMPARABLE_PRODUCTS_UNAVAILABLE = "requirement_not_met:≥2_comparable_products"
    DELIVERY_REQUIREMENT_UNAVAILABLE = "requirement_not_met:delivery_data_available"
    PRICE_HISTORY_UNAVAILABLE = "requirement_not_met:price_history_available"
    SIMILAR_PRODUCTS_UNAVAILABLE = "requirement_not_met:≥3_similar_in_stock"
    EMI_UNAVAILABLE = "requirement_not_met:emi_eligible"
    PAYMENT_FAILURE_REQUIRED = "requirement_not_met:payment_failure_occurred"
    CHECKOUT_REQUIRED = "requirement_not_met:checkout_started"
    DISCOUNT_BUDGET_UNAVAILABLE = "requirement_not_met:discount_budget_available"
    CART_VALUE_REQUIREMENT = "requirement_not_met:cart_value≥5000"
    DISCOUNT_CART_VALUE_REQUIREMENT = "requirement_not_met:cart_value≥1000"
    CART_VALUE_BELOW_EMI_THRESHOLD = "cart_value_below_emi_threshold"
    EQUIVALENT_COUPON_ALREADY_APPLIED = "equivalent_coupon_already_applied"
    DELIVERY_DATA_UNAVAILABLE = "delivery_data_unavailable"
    NO_GROUNDED_SUMMARY_AVAILABLE = "no_grounded_summary_available"
    DISCOUNT_RISK_BELOW_HIGH_THRESHOLD = "discount_risk_below_high_threshold"
    CART_VALUE_BELOW_DISCOUNT_THRESHOLD = "cart_value_below_discount_threshold"
    RECOMMENDATION_CONFIDENCE_BELOW_DISCOUNT_THRESHOLD = (
        "recommendation_confidence_below_discount_threshold"
    )
    LOW_COST_ALTERNATIVE_AVAILABLE = "low_cost_alternative_available"
    PRICE_SENSITIVITY_NOT_VERIFIED = "price_sensitivity_not_verified"


REQUIREMENT_REASONS = {
    "review_summary_available": PolicyReason.REVIEW_SUMMARY_UNAVAILABLE,
    "≥2_comparable_products": PolicyReason.COMPARABLE_PRODUCTS_UNAVAILABLE,
    "delivery_data_available": PolicyReason.DELIVERY_REQUIREMENT_UNAVAILABLE,
    "price_history_available": PolicyReason.PRICE_HISTORY_UNAVAILABLE,
    "≥3_similar_in_stock": PolicyReason.SIMILAR_PRODUCTS_UNAVAILABLE,
    "emi_eligible": PolicyReason.EMI_UNAVAILABLE,
    "payment_failure_occurred": PolicyReason.PAYMENT_FAILURE_REQUIRED,
    "checkout_started": PolicyReason.CHECKOUT_REQUIRED,
    "discount_budget_available": PolicyReason.DISCOUNT_BUDGET_UNAVAILABLE,
    "cart_value≥5000": PolicyReason.CART_VALUE_REQUIREMENT,
    "cart_value≥1000": PolicyReason.DISCOUNT_CART_VALUE_REQUIREMENT,
}
