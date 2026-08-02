from __future__ import annotations

from backend.domain.causes import RootCause
from backend.domain.interventions import InterventionId


FEATURE_LABELS = {
    "s_review_open_count": "The customer reopened reviews {value:g} times.",
    "s_review_dwell_seconds": "The customer spent {value:g} seconds reading reviews.",
    "s_similar_product_view_count": "The customer viewed {value:g} similar products.",
    "s_price_sort_count": "The customer sorted by price {value:g} times.",
    "s_coupon_search_count": "The customer searched for coupons {value:g} times.",
    "d_check_count": "The customer checked delivery {value:g} times.",
    "pay_failure_count": "The checkout recorded {value:g} failed payment attempts.",
    "pay_method_change_count": "The payment method changed {value:g} times.",
    "s_cart_product_switch_count": "The customer switched cart items {value:g} times.",
    "s_idle_seconds_current": "The session has been idle for {value:g} seconds.",
    "c_value_to_aov_ratio": "The cart is {value:.1f} times the customer's typical order.",
    "c_value": "The cart value is ₹{value:,.0f}.",
}

CAUSE_STATEMENTS = {
    RootCause.PRICE_SENSITIVITY: "Price comparisons and coupon activity indicate price sensitivity.",
    RootCause.PRODUCT_QUALITY_UNCERTAINTY: (
        "Repeated review visits and similar-product browsing indicate unresolved "
        "product-quality concerns."
    ),
    RootCause.CHOICE_OVERLOAD: "Repeated comparison and cart switching indicate choice overload.",
    RootCause.DELIVERY_CONCERN: "Repeated delivery checks indicate delivery concern.",
    RootCause.AFFORDABILITY_OR_EMI_NEED: "The cart value indicates an affordability or EMI need.",
    RootCause.CHECKOUT_OR_PAYMENT_FAILURE: (
        "Payment and checkout signals indicate a checkout-completion barrier."
    ),
    RootCause.PRODUCT_AVAILABILITY_CONCERN: (
        "Stock signals indicate a product-availability concern."
    ),
    RootCause.LOW_PURCHASE_INTENT: "Low activity and idle time indicate weak purchase intent.",
    RootCause.TRUST_OR_RETURN_POLICY_CONCERN: (
        "Customer and product signals indicate a trust or returns concern."
    ),
    RootCause.SESSION_INTERRUPTION_OR_DISTRACTION: (
        "Idle and context signals indicate the session may have been interrupted."
    ),
    RootCause.UNKNOWN: "Signals were conflicting, so no confident diagnosis was made.",
}

INTERVENTION_COPY = {
    InterventionId.REVIEW_SUMMARY: (
        "What shoppers are saying",
        "Repeated review visits suggest product-quality questions—here's a concise summary.",
        "See review highlights",
    ),
    InterventionId.PRODUCT_COMPARISON: (
        "Compare your options",
        "See the important differences side by side before you decide.",
        "Compare products",
    ),
    InterventionId.DELIVERY_REASSURANCE: (
        "Delivery details, made clear",
        "Review the latest delivery estimate and availability for your cart.",
        "View delivery details",
    ),
    InterventionId.RETURN_POLICY_REASSURANCE: (
        "Shop with confidence",
        "Review the return and replacement protections available for this purchase.",
        "View return policy",
    ),
    InterventionId.PRICE_DROP_ALERT: (
        "Track the best price",
        "Turn on a price alert and we'll help you watch for a better deal.",
        "Set price alert",
    ),
    InterventionId.SIMILAR_PRODUCT_RECOMMENDATION: (
        "Explore similar choices",
        "Compare well-rated alternatives without losing your current cart.",
        "View alternatives",
    ),
    InterventionId.EMI_SUGGESTION: (
        "Flexible payment available",
        "Eligible EMI options can spread this purchase across monthly payments.",
        "See EMI options",
    ),
    InterventionId.ALTERNATE_PAYMENT_METHOD: (
        "Try another payment method",
        "Your cart is safe. Choose another payment option to continue checkout.",
        "View payment options",
    ),
    InterventionId.CHECKOUT_ASSISTANCE: (
        "Need help checking out?",
        "Review the remaining checkout steps without losing your cart.",
        "Continue securely",
    ),
    InterventionId.WISHLIST_REMINDER: (
        "Save it for later",
        "Not ready today? Keep these items handy in your wishlist.",
        "Save to wishlist",
    ),
    InterventionId.LIMITED_TIME_DISCOUNT: (
        "A limited saving for this cart",
        "An eligible cart saving is available for a limited time.",
        "View saving",
    ),
    InterventionId.NO_ACTION: (
        "No intervention needed",
        "The current session does not need assistance.",
        "",
    ),
}


def feature_statement(feature: str, value: float) -> str:
    template = FEATURE_LABELS.get(feature, "The {feature} signal is {value:g}.")
    return template.format(feature=feature.replace("_", " "), value=value)


def action_statement(intervention: InterventionId) -> str:
    if intervention == InterventionId.NO_ACTION:
        return "No customer-facing action was selected."
    return f"{INTERVENTION_COPY[intervention][0]} addresses the strongest evidence with a governed action."


def rejection_statement(intervention: str, reasons: list[str]) -> str:
    if intervention == InterventionId.LIMITED_TIME_DISCOUNT.value:
        return "A discount was not offered because its safety conditions were not all satisfied."
    reason = reasons[0].replace("_", " ") if reasons else "lower utility"
    return f"{intervention.replace('_', ' ').title()} was not selected because of {reason}."
