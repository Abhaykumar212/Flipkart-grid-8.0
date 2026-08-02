from enum import StrEnum


class RootCause(StrEnum):
    PRICE_SENSITIVITY = "PRICE_SENSITIVITY"
    PRODUCT_QUALITY_UNCERTAINTY = "PRODUCT_QUALITY_UNCERTAINTY"
    CHOICE_OVERLOAD = "CHOICE_OVERLOAD"
    DELIVERY_CONCERN = "DELIVERY_CONCERN"
    AFFORDABILITY_OR_EMI_NEED = "AFFORDABILITY_OR_EMI_NEED"
    CHECKOUT_OR_PAYMENT_FAILURE = "CHECKOUT_OR_PAYMENT_FAILURE"
    PRODUCT_AVAILABILITY_CONCERN = "PRODUCT_AVAILABILITY_CONCERN"
    LOW_PURCHASE_INTENT = "LOW_PURCHASE_INTENT"
    TRUST_OR_RETURN_POLICY_CONCERN = "TRUST_OR_RETURN_POLICY_CONCERN"
    SESSION_INTERRUPTION_OR_DISTRACTION = "SESSION_INTERRUPTION_OR_DISTRACTION"
    UNKNOWN = "UNKNOWN"


EVIDENCE_FAMILIES: dict[RootCause, tuple[str, ...]] = {
    RootCause.PRICE_SENSITIVITY: (
        "s_price_sort_count",
        "s_coupon_search_count",
        "c_value_to_aov_ratio",
        "u_discount_usage_rate",
        "c_max_price_drop_pct",
    ),
    RootCause.PRODUCT_QUALITY_UNCERTAINTY: (
        "s_review_open_count",
        "s_review_dwell_seconds",
        "s_similar_product_view_count",
        "p_avg_rating",
    ),
    RootCause.CHOICE_OVERLOAD: (
        "s_comparison_count",
        "s_distinct_products_viewed",
        "s_cart_product_switch_count",
    ),
    RootCause.DELIVERY_CONCERN: (
        "d_check_count",
        "d_max_days",
        "d_fee_pct_of_cart",
    ),
    RootCause.AFFORDABILITY_OR_EMI_NEED: (
        "c_value",
        "c_value_to_aov_ratio",
        "pay_emi_eligible",
        "u_avg_order_value",
    ),
    RootCause.CHECKOUT_OR_PAYMENT_FAILURE: (
        "pay_failure_count",
        "pay_method_change_count",
        "pay_checkout_max_step",
    ),
    RootCause.PRODUCT_AVAILABILITY_CONCERN: (
        "p_any_out_of_stock",
        "p_any_low_stock",
    ),
    RootCause.LOW_PURCHASE_INTENT: (
        "s_idle_seconds_current",
        "s_product_view_count",
        "s_cart_add_count",
        "s_event_velocity_per_min",
    ),
    RootCause.TRUST_OR_RETURN_POLICY_CONCERN: (
        "u_return_rate",
        "p_min_rating_count",
        "u_is_new_user",
    ),
    RootCause.SESSION_INTERRUPTION_OR_DISTRACTION: (
        "s_idle_seconds_current",
        "x_is_mobile",
        "x_is_late_night",
        "s_event_velocity_per_min",
    ),
    RootCause.UNKNOWN: (),
}
