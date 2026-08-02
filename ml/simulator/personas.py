from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping

from backend.domain.causes import RootCause
from backend.domain.interventions import InterventionId


class PersonaName(StrEnum):
    PRICE_SENSITIVE = "PRICE_SENSITIVE"
    QUALITY_CONSCIOUS = "QUALITY_CONSCIOUS"
    URGENT_DELIVERY = "URGENT_DELIVERY"
    COMPARISON_HEAVY = "COMPARISON_HEAVY"
    CASUAL_BROWSER = "CASUAL_BROWSER"
    PAYMENT_CONSTRAINED = "PAYMENT_CONSTRAINED"
    HIGH_INTENT_REPEAT = "HIGH_INTENT_REPEAT"
    DISTRACTED_MOBILE = "DISTRACTED_MOBILE"


@dataclass(frozen=True, slots=True)
class Behavior:
    """Observable transition and event-distribution parameters for a persona."""

    product_views_mean: float
    searches_mean: float = 0.3
    price_sort_probability: float = 0.08
    review_opens_mean: float = 0.3
    review_dwell_seconds_mean: float = 8.0
    similar_views_mean: float = 0.3
    comparisons_mean: float = 0.15
    delivery_checks_mean: float = 0.15
    coupon_search_probability: float = 0.08
    cart_churn_probability: float = 0.06
    start_checkout_probability: float = 0.65
    payment_failure_probability: float = 0.03
    change_method_probability: float = 0.75
    back_from_checkout_probability: float = 0.04
    checkout_completion_probability: float = 0.5
    inter_event_seconds_mean: float = 12.0
    idle_gap_probability: float = 0.03
    mobile_probability: float = 0.55
    late_night_probability: float = 0.08


@dataclass(frozen=True, slots=True)
class Persona:
    name: PersonaName
    mix: float
    base_abandonment: float
    causes: Mapping[RootCause, float]
    behavior: Behavior
    uplift: Mapping[tuple[InterventionId, RootCause], float] = field(
        default_factory=dict
    )


def _uplift(
    *rows: tuple[InterventionId, RootCause, float],
) -> dict[tuple[InterventionId, RootCause], float]:
    return {(intervention, cause): value for intervention, cause, value in rows}


COMMON_CONTEXT_UPLIFT = _uplift(
    (
        InterventionId.SIMILAR_PRODUCT_RECOMMENDATION,
        RootCause.PRODUCT_AVAILABILITY_CONCERN,
        0.24,
    ),
    (
        InterventionId.RETURN_POLICY_REASSURANCE,
        RootCause.TRUST_OR_RETURN_POLICY_CONCERN,
        0.22,
    ),
)


def _with_context(
    rows: Mapping[tuple[InterventionId, RootCause], float],
) -> dict[tuple[InterventionId, RootCause], float]:
    return {**COMMON_CONTEXT_UPLIFT, **rows}


# The eight frozen personas from IMPLEMENTATION_PLAN.md section 10.1. Checkout
# probabilities are transition parameters, calibrated so the product of the
# natural cart -> checkout -> payment -> completion path realizes each base
# abandonment rate; the outcome itself is never drawn from a standalone label
# formula.
PERSONAS: tuple[Persona, ...] = (
    Persona(
        PersonaName.PRICE_SENSITIVE,
        0.18,
        0.72,
        {RootCause.PRICE_SENSITIVITY: 0.85},
        Behavior(
            product_views_mean=3.4,
            searches_mean=2.4,
            price_sort_probability=0.78,
            review_opens_mean=0.25,
            coupon_search_probability=0.78,
            cart_churn_probability=0.12,
            start_checkout_probability=0.65,
            checkout_completion_probability=0.46,
            inter_event_seconds_mean=18,
        ),
        _with_context(_uplift(
            (InterventionId.PRICE_DROP_ALERT, RootCause.PRICE_SENSITIVITY, 0.28),
            (
                InterventionId.LIMITED_TIME_DISCOUNT,
                RootCause.PRICE_SENSITIVITY,
                0.41,
            ),
        )),
    ),
    Persona(
        PersonaName.QUALITY_CONSCIOUS,
        0.16,
        0.65,
        {RootCause.PRODUCT_QUALITY_UNCERTAINTY: 0.88},
        Behavior(
            product_views_mean=3.2,
            review_opens_mean=5.2,
            review_dwell_seconds_mean=39,
            similar_views_mean=3.1,
            comparisons_mean=0.7,
            start_checkout_probability=0.72,
            checkout_completion_probability=0.51,
            inter_event_seconds_mean=16,
        ),
        _with_context(_uplift(
            (
                InterventionId.REVIEW_SUMMARY,
                RootCause.PRODUCT_QUALITY_UNCERTAINTY,
                0.34,
            ),
            (
                InterventionId.RETURN_POLICY_REASSURANCE,
                RootCause.PRODUCT_QUALITY_UNCERTAINTY,
                0.16,
            ),
            (
                InterventionId.LIMITED_TIME_DISCOUNT,
                RootCause.PRODUCT_QUALITY_UNCERTAINTY,
                0.03,
            ),
        )),
    ),
    Persona(
        PersonaName.URGENT_DELIVERY,
        0.12,
        0.70,
        {RootCause.DELIVERY_CONCERN: 0.86},
        Behavior(
            product_views_mean=2.2,
            delivery_checks_mean=4.2,
            start_checkout_probability=0.68,
            checkout_completion_probability=0.47,
            inter_event_seconds_mean=10,
        ),
        _with_context(_uplift(
            (
                InterventionId.DELIVERY_REASSURANCE,
                RootCause.DELIVERY_CONCERN,
                0.31,
            ),
            (
                InterventionId.LIMITED_TIME_DISCOUNT,
                RootCause.DELIVERY_CONCERN,
                0.05,
            ),
        )),
    ),
    Persona(
        PersonaName.COMPARISON_HEAVY,
        0.14,
        0.74,
        {
            RootCause.CHOICE_OVERLOAD: 0.79,
            RootCause.PRODUCT_QUALITY_UNCERTAINTY: 0.42,
        },
        Behavior(
            product_views_mean=5.4,
            searches_mean=1.1,
            review_opens_mean=1.1,
            similar_views_mean=2.4,
            comparisons_mean=3.4,
            cart_churn_probability=0.32,
            start_checkout_probability=0.62,
            checkout_completion_probability=0.45,
            inter_event_seconds_mean=17,
        ),
        _with_context(_uplift(
            (InterventionId.PRODUCT_COMPARISON, RootCause.CHOICE_OVERLOAD, 0.30),
            (
                InterventionId.REVIEW_SUMMARY,
                RootCause.PRODUCT_QUALITY_UNCERTAINTY,
                0.18,
            ),
            (
                InterventionId.LIMITED_TIME_DISCOUNT,
                RootCause.CHOICE_OVERLOAD,
                0.08,
            ),
        )),
    ),
    Persona(
        PersonaName.CASUAL_BROWSER,
        0.14,
        0.88,
        {RootCause.LOW_PURCHASE_INTENT: 0.83},
        Behavior(
            product_views_mean=7.2,
            searches_mean=1.4,
            review_opens_mean=0.15,
            similar_views_mean=1.0,
            cart_churn_probability=0.15,
            start_checkout_probability=0.38,
            back_from_checkout_probability=0.10,
            checkout_completion_probability=0.37,
            inter_event_seconds_mean=31,
            idle_gap_probability=0.18,
        ),
        _with_context(_uplift(
            (InterventionId.WISHLIST_REMINDER, RootCause.LOW_PURCHASE_INTENT, 0.12),
            (
                InterventionId.LIMITED_TIME_DISCOUNT,
                RootCause.LOW_PURCHASE_INTENT,
                0.04,
            ),
        )),
    ),
    Persona(
        PersonaName.PAYMENT_CONSTRAINED,
        0.10,
        0.69,
        {
            RootCause.CHECKOUT_OR_PAYMENT_FAILURE: 0.74,
            RootCause.AFFORDABILITY_OR_EMI_NEED: 0.61,
        },
        Behavior(
            product_views_mean=2.0,
            coupon_search_probability=0.32,
            start_checkout_probability=0.90,
            payment_failure_probability=0.65,
            change_method_probability=0.70,
            back_from_checkout_probability=0.03,
            checkout_completion_probability=0.40,
            inter_event_seconds_mean=11,
        ),
        _with_context(_uplift(
            (
                InterventionId.ALTERNATE_PAYMENT_METHOD,
                RootCause.CHECKOUT_OR_PAYMENT_FAILURE,
                0.35,
            ),
            (
                InterventionId.EMI_SUGGESTION,
                RootCause.AFFORDABILITY_OR_EMI_NEED,
                0.29,
            ),
            (
                InterventionId.CHECKOUT_ASSISTANCE,
                RootCause.CHECKOUT_OR_PAYMENT_FAILURE,
                0.22,
            ),
            (
                InterventionId.LIMITED_TIME_DISCOUNT,
                RootCause.AFFORDABILITY_OR_EMI_NEED,
                0.09,
            ),
        )),
    ),
    Persona(
        PersonaName.HIGH_INTENT_REPEAT,
        0.06,
        0.14,
        {},
        Behavior(
            product_views_mean=1.1,
            searches_mean=0.05,
            review_opens_mean=0.05,
            start_checkout_probability=0.97,
            payment_failure_probability=0.01,
            change_method_probability=0.95,
            back_from_checkout_probability=0.01,
            checkout_completion_probability=0.90,
            inter_event_seconds_mean=3,
            mobile_probability=0.35,
        ),
        _with_context({}),
    ),
    Persona(
        PersonaName.DISTRACTED_MOBILE,
        0.10,
        0.79,
        {RootCause.SESSION_INTERRUPTION_OR_DISTRACTION: 0.77},
        Behavior(
            product_views_mean=3.0,
            searches_mean=0.7,
            review_opens_mean=0.45,
            start_checkout_probability=0.56,
            back_from_checkout_probability=0.10,
            checkout_completion_probability=0.43,
            inter_event_seconds_mean=24,
            idle_gap_probability=0.34,
            mobile_probability=0.96,
            late_night_probability=0.72,
        ),
        _with_context(_uplift(
            (
                InterventionId.WISHLIST_REMINDER,
                RootCause.SESSION_INTERRUPTION_OR_DISTRACTION,
                0.19,
            ),
            (
                InterventionId.LIMITED_TIME_DISCOUNT,
                RootCause.SESSION_INTERRUPTION_OR_DISTRACTION,
                0.06,
            ),
        )),
    ),
)

PERSONA_BY_NAME = {persona.name: persona for persona in PERSONAS}
PERSONA_NAMES = tuple(persona.name.value for persona in PERSONAS)
PERSONA_MIX = tuple(persona.mix for persona in PERSONAS)

assert abs(sum(PERSONA_MIX) - 1.0) < 1e-9
