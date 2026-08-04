from __future__ import annotations

from backend.domain.causes import RootCause
from backend.domain.interventions import InterventionId

from .narratives import NARRATIVES, informative, statement

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
    InterventionId.STOCK_SCARCITY_NUDGE: (
        "Limited stock on this item",
        "Only a few units are left with this seller right now.",
        "View availability",
    ),
    InterventionId.EXIT_INTENT_REMINDER: (
        "Before you go",
        "Your selection is saved. Pick up exactly where you left off whenever you're ready.",
        "Keep my selection",
    ),
    InterventionId.TRUST_BADGE_REASSURANCE: (
        "Protected on every order",
        "Secure payments, verified sellers and a 7-day replacement window apply here.",
        "View protections",
    ),
    InterventionId.SAVED_PAYMENT_PROMPT: (
        "Save a payment method",
        "Storing a payment method removes the slowest step next time you check out.",
        "Save for next time",
    ),
    InterventionId.GUEST_ACCOUNT_NUDGE: (
        "Track this order easily",
        "Create an account in one tap for order tracking and faster reordering.",
        "Create account",
    ),
    InterventionId.DELIVERY_SPEED_UPGRADE: (
        "A faster delivery slot",
        "An earlier delivery window is available for this order.",
        "See faster delivery",
    ),
    InterventionId.FREE_DELIVERY_WAIVER: (
        "Delivery fee waived",
        "The delivery fee on this order has been covered for you.",
        "View updated total",
    ),
    InterventionId.NO_ACTION: (
        "No intervention needed",
        "The current session does not need assistance.",
        "",
    ),
}


def feature_statement(feature: str, value: float) -> str:
    """Render one feature reading as a complete English sentence."""

    return statement(feature, value)


def feature_is_informative(feature: str, value: float) -> bool:
    """Whether this reading is worth putting in front of a human."""

    return informative(feature, value)


#: Retained for callers that only need the sentence templates.
FEATURE_LABELS = {name: item.template for name, item in NARRATIVES.items()}


def action_statement(intervention: InterventionId) -> str:
    if intervention == InterventionId.NO_ACTION:
        return "No customer-facing action was selected."
    return f"{INTERVENTION_COPY[intervention][0]} addresses the strongest evidence with a governed action."


def rejection_statement(intervention: str, reasons: list[str]) -> str:
    if intervention == InterventionId.LIMITED_TIME_DISCOUNT.value:
        return "A discount was not offered because its safety conditions were not all satisfied."
    reason = reasons[0].replace("_", " ") if reasons else "lower utility"
    return f"{intervention.replace('_', ' ').title()} was not selected because of {reason}."
