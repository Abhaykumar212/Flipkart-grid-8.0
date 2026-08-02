from backend.domain.causes import RootCause
from backend.domain.enums import Channel, CostLevel
from backend.domain.interventions import InterventionDefinition, InterventionId


def _definition(
    intervention_id: InterventionId,
    supported_causes: tuple[RootCause | str, ...],
    cost_level: CostLevel,
    intrusiveness: int,
    cooldown_minutes: int,
    allowed_channels: tuple[Channel, ...],
    requires: tuple[str, ...],
    prior_uplift: float,
    *,
    max_discount_pct: float | None = None,
) -> InterventionDefinition:
    return InterventionDefinition(
        intervention_id=intervention_id,
        display_name=intervention_id.value.replace("_", " ").title(),
        supported_causes=supported_causes,
        cost_level=cost_level,
        intrusiveness=intrusiveness,
        cooldown_minutes=cooldown_minutes,
        allowed_channels=allowed_channels,
        requires=requires,
        prior_uplift=prior_uplift,
        max_discount_pct=max_discount_pct,
    )


INTERVENTION_CATALOGUE = (
    _definition(InterventionId.REVIEW_SUMMARY, (RootCause.PRODUCT_QUALITY_UNCERTAINTY,), CostLevel.LOW, 1, 15, (Channel.INLINE_CARD, Channel.ASSISTANT_PANEL), ("review_summary_available",), 0.28),
    _definition(InterventionId.PRODUCT_COMPARISON, (RootCause.CHOICE_OVERLOAD,), CostLevel.LOW, 1, 15, (Channel.COMPARISON_DRAWER, Channel.ASSISTANT_PANEL), ("≥2_comparable_products",), 0.26),
    _definition(InterventionId.DELIVERY_REASSURANCE, (RootCause.DELIVERY_CONCERN,), CostLevel.LOW, 1, 10, (Channel.INLINE_CARD, Channel.BANNER), ("delivery_data_available",), 0.27),
    _definition(InterventionId.RETURN_POLICY_REASSURANCE, (RootCause.TRUST_OR_RETURN_POLICY_CONCERN,), CostLevel.LOW, 1, 20, (Channel.INLINE_CARD, Channel.ASSISTANT_PANEL), (), 0.19),
    _definition(InterventionId.PRICE_DROP_ALERT, (RootCause.PRICE_SENSITIVITY,), CostLevel.LOW, 1, 20, (Channel.INLINE_CARD, Channel.BANNER), ("price_history_available",), 0.24),
    _definition(InterventionId.SIMILAR_PRODUCT_RECOMMENDATION, (RootCause.PRICE_SENSITIVITY, RootCause.PRODUCT_AVAILABILITY_CONCERN), CostLevel.LOW, 2, 20, (Channel.COMPARISON_DRAWER, Channel.INLINE_CARD), ("≥3_similar_in_stock",), 0.21),
    _definition(InterventionId.EMI_SUGGESTION, (RootCause.AFFORDABILITY_OR_EMI_NEED,), CostLevel.LOW, 1, 30, (Channel.INLINE_CARD, Channel.CHECKOUT_PANEL), ("emi_eligible", "cart_value≥5000"), 0.25),
    _definition(InterventionId.ALTERNATE_PAYMENT_METHOD, (RootCause.CHECKOUT_OR_PAYMENT_FAILURE,), CostLevel.LOW, 1, 5, (Channel.CHECKOUT_PANEL,), ("payment_failure_occurred",), 0.33),
    _definition(InterventionId.CHECKOUT_ASSISTANCE, (RootCause.CHECKOUT_OR_PAYMENT_FAILURE,), CostLevel.LOW, 2, 10, (Channel.CHECKOUT_PANEL, Channel.ASSISTANT_PANEL), ("checkout_started",), 0.22),
    _definition(InterventionId.WISHLIST_REMINDER, (RootCause.LOW_PURCHASE_INTENT, RootCause.SESSION_INTERRUPTION_OR_DISTRACTION), CostLevel.LOW, 1, 30, (Channel.BANNER, Channel.INLINE_CARD), (), 0.14),
    _definition(InterventionId.LIMITED_TIME_DISCOUNT, (RootCause.PRICE_SENSITIVITY,), CostLevel.HIGH, 3, 60, (Channel.INLINE_CARD, Channel.BANNER), ("discount_budget_available", "cart_value≥1000"), 0.38, max_discount_pct=10.0),
    _definition(InterventionId.NO_ACTION, ("*",), CostLevel.ZERO, 0, 0, (), (), 0.0),
)

CATALOGUE_BY_ID = {item.intervention_id: item for item in INTERVENTION_CATALOGUE}
