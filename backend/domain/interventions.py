from dataclasses import dataclass
from enum import StrEnum

from .causes import RootCause
from .enums import Channel, CostLevel


class InterventionId(StrEnum):
    REVIEW_SUMMARY = "REVIEW_SUMMARY"
    PRODUCT_COMPARISON = "PRODUCT_COMPARISON"
    DELIVERY_REASSURANCE = "DELIVERY_REASSURANCE"
    RETURN_POLICY_REASSURANCE = "RETURN_POLICY_REASSURANCE"
    PRICE_DROP_ALERT = "PRICE_DROP_ALERT"
    SIMILAR_PRODUCT_RECOMMENDATION = "SIMILAR_PRODUCT_RECOMMENDATION"
    EMI_SUGGESTION = "EMI_SUGGESTION"
    ALTERNATE_PAYMENT_METHOD = "ALTERNATE_PAYMENT_METHOD"
    CHECKOUT_ASSISTANCE = "CHECKOUT_ASSISTANCE"
    WISHLIST_REMINDER = "WISHLIST_REMINDER"
    LIMITED_TIME_DISCOUNT = "LIMITED_TIME_DISCOUNT"
    STOCK_SCARCITY_NUDGE = "STOCK_SCARCITY_NUDGE"
    EXIT_INTENT_REMINDER = "EXIT_INTENT_REMINDER"
    FREE_DELIVERY_WAIVER = "FREE_DELIVERY_WAIVER"
    DELIVERY_SPEED_UPGRADE = "DELIVERY_SPEED_UPGRADE"
    TRUST_BADGE_REASSURANCE = "TRUST_BADGE_REASSURANCE"
    SAVED_PAYMENT_PROMPT = "SAVED_PAYMENT_PROMPT"
    GUEST_ACCOUNT_NUDGE = "GUEST_ACCOUNT_NUDGE"
    NO_ACTION = "NO_ACTION"


#: Levers that cost real margin when they fire. `policy_engine` routes all of
#: these through discount protection, not just the headline discount.
MARGIN_SPENDING = frozenset({
    InterventionId.LIMITED_TIME_DISCOUNT,
    InterventionId.FREE_DELIVERY_WAIVER,
    InterventionId.DELIVERY_SPEED_UPGRADE,
})


@dataclass(frozen=True, slots=True)
class InterventionDefinition:
    intervention_id: InterventionId
    display_name: str
    supported_causes: tuple[RootCause | str, ...]
    cost_level: CostLevel
    intrusiveness: int
    cooldown_minutes: int
    allowed_channels: tuple[Channel, ...]
    requires: tuple[str, ...]
    prior_uplift: float
    max_discount_pct: float | None = None
    is_active: bool = True
