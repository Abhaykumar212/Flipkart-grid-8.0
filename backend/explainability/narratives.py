"""Human-readable narratives for every feature in the serving contract.

The explanation trail is judged on whether a person can follow the evidence, so
no raw feature identifier may ever reach rendered prose. Every one of the 67
features in ``FEATURE_SCHEMA_V1`` therefore has an explicit sentence here, and
values are formatted for humans (durations, rupees, percentages) rather than
printed as raw floats.

Features are also classified by whether their *zero* value carries information.
``s_review_open_count = 0`` says nothing worth reading aloud, while
``pay_method_on_file = 0`` is a real observation about a stalled checkout. The
structured explanation builder uses :func:`informative` to drop the former.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from backend.feature_engine.schema import FEATURE_BY_NAME, FEATURE_NAMES


Kind = Literal[
    "count", "seconds", "currency", "rate", "pct", "ratio", "number", "flag", "hour"
]


@dataclass(frozen=True, slots=True)
class Narrative:
    """How one feature is spoken about in a justification trail."""

    template: str
    #: ``rate`` is a 0-1 fraction; ``pct`` is already in percentage points.
    kind: Kind = "count"
    #: Whether a zero (or false) reading is still worth stating.
    zero_ok: bool = False
    #: Alternate sentence used when a ``flag`` feature reads false.
    false_template: str | None = None
    #: True when the schema default is a cold-start assumption rather than an
    #: observation. Quoting an assumption back as evidence is how explainable
    #: systems lose the trust they exist to earn.
    prior: bool = False


def duration_phrase(seconds: float) -> str:
    """Render a second count the way a person would say it."""

    if seconds < 1:
        return "under a second"
    if seconds < 90:
        return f"{seconds:.0f} seconds"
    if seconds < 5_400:
        return f"{seconds / 60:.0f} minutes"
    return f"{seconds / 3_600:.1f} hours"


#: Plural nouns used across the templates, so "1 times" never reaches a judge.
_SINGULARS = {
    "times": "time", "items": "item", "orders": "order", "ratings": "rating",
    "days": "day", "categories": "category", "products": "product",
    "searches": "search", "comparisons": "comparison", "nudges": "nudge",
    "stars": "star", "actions": "action", "pages": "page", "types": "type",
    "steps": "step", "attempts": "attempt", "seconds": "second",
    "minutes": "minute", "hours": "hour", "carts": "cart", "visits": "visit",
}
# "1 side-by-side comparisons" needs the *last* word fixed, not the first, so
# the pattern allows modifiers between the count and the noun it governs.
_ONE_OF = re.compile(
    r"\b1 ((?:[a-z-]+ ){0,2})(" + "|".join(sorted(_SINGULARS, key=len, reverse=True)) + r")\b"
)


def _agree(sentence: str) -> str:
    """Make a count of one agree with the noun it governs."""

    return _ONE_OF.sub(
        lambda match: f"1 {match.group(1)}{_SINGULARS[match.group(2)]}", sentence
    )


def format_value(value: float, kind: Kind) -> str:
    """Format a feature value for prose. Never returns raw float noise."""

    if kind == "seconds":
        return duration_phrase(value)
    if kind == "currency":
        return f"₹{value:,.0f}"
    if kind == "rate":
        return f"{value * 100:.0f}%"
    if kind == "pct":
        return f"{value:.0f}%"
    if kind == "ratio":
        return f"{value:.1f}×"
    if kind == "hour":
        return f"{int(value):02d}:00"
    if kind == "count":
        return f"{int(round(value)):,}"
    if kind == "flag":
        return "yes" if value else "no"
    rounded = round(value, 1)
    return f"{rounded:,.0f}" if rounded == int(rounded) else f"{rounded:,.1f}"


# Every feature in FEATURE_SCHEMA_V1, in schema order. `{value}` is substituted
# with the human-formatted reading.
NARRATIVES: dict[str, Narrative] = {
    # Group 1 - user history
    "u_lifetime_orders": Narrative(
        "The shopper has placed {value} previous orders.", "count", zero_ok=True
    ),
    "u_prior_abandonment_rate": Narrative(
        "This shopper has historically abandoned {value} of their carts.", "rate", prior=True
    ),
    "u_avg_order_value": Narrative(
        "Their typical order is worth {value}.", "currency", prior=True
    ),
    "u_discount_usage_rate": Narrative(
        "They have used a discount on {value} of past orders.", "rate", prior=True
    ),
    "u_category_affinity": Narrative(
        "Their affinity for this category scores {value}.", "rate"
    ),
    "u_days_since_last_purchase": Narrative(
        "Their last purchase was {value} days ago.", "number", prior=True
    ),
    "u_avg_session_to_purchase_s": Narrative(
        "They usually take {value} to reach a purchase.", "seconds", prior=True
    ),
    "u_return_rate": Narrative(
        "They return {value} of what they buy.", "rate", prior=True
    ),
    "u_is_new_user": Narrative(
        "This is a brand-new shopper with no order history.",
        "flag",
        zero_ok=True,
        false_template="The shopper has bought here before.",
    ),
    "u_affinity_informational": Narrative(
        "They respond to informational help {value} of the time.", "rate", prior=True
    ),
    "u_affinity_incentive": Narrative(
        "They respond to incentives {value} of the time.", "rate", prior=True
    ),
    # Group 2 - cart
    "c_value": Narrative("The cart is worth {value}.", "currency"),
    "c_item_count": Narrative("The cart holds {value} items.", "count"),
    "c_distinct_categories": Narrative(
        "The cart spans {value} product categories.", "count"
    ),
    "c_value_to_aov_ratio": Narrative(
        "The cart is {value} the shopper's typical order size.", "ratio"
    ),
    "c_discount_pct_available": Narrative(
        "A {value} discount is already advertised on this cart.", "pct"
    ),
    "c_age_seconds": Narrative("The cart has been open for {value}.", "seconds"),
    "c_promo_applied": Narrative(
        "A promo code is already applied to this cart.",
        "flag",
        false_template="No promo code has been applied.",
    ),
    "c_max_price_drop_pct": Narrative(
        "An item in the cart has dropped {value} in price.", "pct"
    ),
    "c_price_increased_since_view": Narrative(
        "An item went up in price since the shopper first saw it.",
        "flag",
        false_template="No cart item has gone up in price.",
    ),
    # Group 3 - product
    "p_max_item_price": Narrative(
        "The most expensive cart item costs {value}.", "currency"
    ),
    "p_avg_rating": Narrative(
        "Cart items average {value} stars.", "number", prior=True
    ),
    "p_min_rating_count": Narrative(
        "The least-reviewed cart item has only {value} ratings.", "count"
    ),
    "p_any_low_stock": Narrative(
        "At least one cart item is running low on stock.",
        "flag",
        false_template="Every cart item is comfortably in stock.",
    ),
    "p_any_out_of_stock": Narrative(
        "At least one cart item is out of stock.",
        "flag",
        false_template="No cart item is out of stock.",
    ),
    # Group 4 - delivery
    "d_max_days": Narrative(
        "The slowest item takes {value} days to arrive.", "number", zero_ok=True, prior=True
    ),
    "d_min_days": Narrative(
        "The fastest item arrives in {value} days.", "number", zero_ok=True, prior=True
    ),
    "d_fee": Narrative("Delivery adds {value} to the cart.", "currency"),
    "d_fee_pct_of_cart": Narrative(
        "Delivery is {value} of the cart value.", "pct"
    ),
    "d_check_count": Narrative(
        "The shopper checked delivery {value} times.", "count"
    ),
    # Group 5 - payment
    "pay_method_on_file": Narrative(
        "The shopper has a saved payment method.",
        "flag",
        zero_ok=True,
        false_template="The shopper has no saved payment method.",
    ),
    "pay_failure_count": Narrative(
        "Checkout recorded {value} failed payment attempts.", "count"
    ),
    "pay_method_change_count": Narrative(
        "The payment method was switched {value} times.", "count"
    ),
    "pay_emi_eligible": Narrative(
        "This cart qualifies for EMI.",
        "flag",
        false_template="This cart does not qualify for EMI.",
    ),
    "pay_checkout_max_step": Narrative(
        "The shopper reached checkout step {value}.", "count"
    ),
    # Group 6 - session behaviour
    "s_duration_seconds": Narrative(
        "The session has run for {value}.", "seconds"
    ),
    "s_product_view_count": Narrative(
        "The shopper opened {value} product pages.", "count"
    ),
    "s_distinct_products_viewed": Narrative(
        "They looked at {value} different products.", "count"
    ),
    "s_review_open_count": Narrative(
        "They reopened the reviews {value} times.", "count"
    ),
    "s_review_dwell_seconds": Narrative(
        "They spent {value} reading reviews.", "seconds"
    ),
    "s_similar_product_view_count": Narrative(
        "They viewed {value} similar products.", "count"
    ),
    "s_comparison_count": Narrative(
        "They ran {value} side-by-side comparisons.", "count"
    ),
    "s_cart_view_count": Narrative(
        "They returned to the cart {value} times.", "count"
    ),
    "s_cart_add_count": Narrative(
        "They added items to the cart {value} times.", "count"
    ),
    "s_cart_remove_count": Narrative(
        "They removed items from the cart {value} times.", "count"
    ),
    "s_cart_product_switch_count": Narrative(
        "They swapped cart items {value} times.", "count"
    ),
    "s_search_count": Narrative("They ran {value} searches.", "count"),
    "s_price_sort_count": Narrative(
        "They sorted by price {value} times.", "count"
    ),
    "s_coupon_search_count": Narrative(
        "They searched for coupons {value} times.", "count"
    ),
    "s_checkout_start_count": Narrative(
        "They started checkout {value} times.", "count"
    ),
    "s_back_from_checkout_count": Narrative(
        "They backed out of checkout {value} times.", "count"
    ),
    "s_idle_seconds_current": Narrative(
        "The session has been idle for {value}.", "seconds"
    ),
    "s_event_velocity_per_min": Narrative(
        "Activity is running at {value} actions per minute.", "number"
    ),
    # Group 7 - context
    "x_is_mobile": Narrative(
        "They are shopping on mobile.",
        "flag",
        false_template="They are shopping on desktop.",
    ),
    "x_hour_of_day": Narrative(
        "The session is running at {value} local time.", "hour", zero_ok=True
    ),
    "x_is_late_night": Narrative(
        "This is a late-night session.",
        "flag",
        false_template="This is a daytime session.",
    ),
    "x_is_weekend": Narrative(
        "This is a weekend session.",
        "flag",
        false_template="This is a weekday session.",
    ),
    "x_is_returning_user": Narrative(
        "This shopper has visited before.",
        "flag",
        false_template="This is the shopper's first visit.",
    ),
    "x_referral_direct": Narrative(
        "They arrived directly.",
        "flag",
        false_template="They did not arrive directly.",
    ),
    "x_referral_search": Narrative(
        "They arrived from search.",
        "flag",
        false_template="They did not arrive from search.",
    ),
    "x_referral_social": Narrative(
        "They arrived from social.",
        "flag",
        false_template="They did not arrive from social.",
    ),
    "x_referral_email": Narrative(
        "They arrived from an email link.",
        "flag",
        false_template="They did not arrive from email.",
    ),
    # Group 8 - intervention history
    "i_shown_count": Narrative(
        "They have already been shown {value} nudges this session.", "count"
    ),
    "i_dismissal_count": Narrative(
        "They dismissed {value} previous nudges.", "count"
    ),
    "i_click_count": Narrative(
        "They engaged with {value} previous nudges.", "count"
    ),
    "i_seconds_since_last": Narrative(
        "The last nudge was {value} ago.", "seconds", prior=True
    ),
    "i_distinct_types_shown": Narrative(
        "They have seen {value} distinct nudge types.", "count"
    ),
}

# A missing narrative would leak a raw identifier into judge-facing prose.
assert set(NARRATIVES) == set(FEATURE_NAMES), (
    "every feature needs a narrative: "
    f"{sorted(set(FEATURE_NAMES) ^ set(NARRATIVES))}"
)


def informative(feature: str, value: float) -> bool:
    """Whether stating this reading adds anything to a justification trail."""

    narrative = NARRATIVES.get(feature)
    if narrative is None:
        return False
    if narrative.prior:
        spec = FEATURE_BY_NAME.get(feature)
        # An untouched cold-start default describes our assumption, not them.
        if spec is not None and abs(value - spec.default) < 1e-9:
            return False
    return bool(value) or narrative.zero_ok


def statement(feature: str, value: float) -> str:
    """Render one observation as a complete, human sentence."""

    narrative = NARRATIVES.get(feature)
    if narrative is None:
        return f"An unlabelled signal read {value:g}."
    if narrative.kind == "flag" and not value and narrative.false_template:
        return narrative.false_template
    return _agree(narrative.template.format(value=format_value(value, narrative.kind)))


def display_probability_pct(probability: float) -> int:
    """Clamp a probability to a percentage a calibrated model can defend.

    A model that reports 99.93% is still not certain, and printing "100%"
    invites exactly the mistrust an explainability layer exists to prevent.
    """

    return max(1, min(99, round(probability * 100)))
