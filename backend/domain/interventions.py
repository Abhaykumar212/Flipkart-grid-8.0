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
    NO_ACTION = "NO_ACTION"


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
