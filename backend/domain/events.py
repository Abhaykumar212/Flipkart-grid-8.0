from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventType(StrEnum):
    SESSION_STARTED = "SESSION_STARTED"
    SEARCH_PERFORMED = "SEARCH_PERFORMED"
    PRODUCT_VIEWED = "PRODUCT_VIEWED"
    REVIEW_OPENED = "REVIEW_OPENED"
    REVIEW_DWELL_RECORDED = "REVIEW_DWELL_RECORDED"
    SIMILAR_PRODUCT_VIEWED = "SIMILAR_PRODUCT_VIEWED"
    PRODUCT_COMPARED = "PRODUCT_COMPARED"
    ITEM_ADDED_TO_CART = "ITEM_ADDED_TO_CART"
    ITEM_REMOVED_FROM_CART = "ITEM_REMOVED_FROM_CART"
    CART_VIEWED = "CART_VIEWED"
    DELIVERY_CHECKED = "DELIVERY_CHECKED"
    COUPON_SEARCHED = "COUPON_SEARCHED"
    CHECKOUT_STARTED = "CHECKOUT_STARTED"
    CHECKOUT_STEP_VIEWED = "CHECKOUT_STEP_VIEWED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_METHOD_CHANGED = "PAYMENT_METHOD_CHANGED"
    INTERVENTION_SHOWN = "INTERVENTION_SHOWN"
    INTERVENTION_CLICKED = "INTERVENTION_CLICKED"
    INTERVENTION_DISMISSED = "INTERVENTION_DISMISSED"
    ORDER_COMPLETED = "ORDER_COMPLETED"
    SESSION_ENDED = "SESSION_ENDED"


class MetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionStartedMetadata(MetadataModel):
    device_type: str
    referral_source: str
    viewport_width: Annotated[int, Field(gt=0)]


class SearchPerformedMetadata(MetadataModel):
    query: str
    result_count: Annotated[int, Field(ge=0)]
    sort_order: str


class SourceMetadata(MetadataModel):
    source: str


class ReviewDwellMetadata(MetadataModel):
    dwell_ms: Annotated[int, Field(ge=0)]


class SimilarProductMetadata(MetadataModel):
    origin_product_id: str


class ProductComparedMetadata(MetadataModel):
    compared_with: list[str]


class ItemAddedMetadata(MetadataModel):
    quantity: Annotated[int, Field(gt=0)]
    unit_price: Annotated[float, Field(gt=0)]
    variant: str | None = None


class ItemRemovedMetadata(MetadataModel):
    quantity: Annotated[int, Field(gt=0)]


class CartMetadata(MetadataModel):
    cart_value: Annotated[float, Field(ge=0)]
    item_count: Annotated[int, Field(ge=0)]


class DeliveryCheckedMetadata(MetadataModel):
    pincode: str
    estimated_days: Annotated[int, Field(ge=0)]
    available: bool

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, value: str) -> str:
        if len(value) != 6 or not value.isdigit():
            raise ValueError("pincode must contain exactly 6 digits")
        return value


class CouponSearchedMetadata(MetadataModel):
    code: str | None = None
    applied: bool


class CheckoutStepMetadata(MetadataModel):
    step: Annotated[int, Field(ge=1, le=3)]
    step_name: str


class PaymentFailedMetadata(MetadataModel):
    method: str
    reason_code: str
    attempt_no: Annotated[int, Field(gt=0)]


class PaymentMethodChangedMetadata(MetadataModel):
    from_method: str
    to_method: str


class InterventionShownMetadata(MetadataModel):
    decision_id: str
    intervention_id: str
    surface: str


class InterventionOutcomeMetadata(MetadataModel):
    decision_id: str
    intervention_id: str


class OrderCompletedMetadata(MetadataModel):
    order_id: str
    order_value: Annotated[float, Field(gt=0)]
    payment_method: str


class SessionEndedMetadata(MetadataModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if value not in {"EXPLICIT", "TIMEOUT", "UNLOAD"}:
            raise ValueError("reason must be EXPLICIT, TIMEOUT, or UNLOAD")
        return value


Metadata = (
    SessionStartedMetadata
    | SearchPerformedMetadata
    | SourceMetadata
    | ReviewDwellMetadata
    | SimilarProductMetadata
    | ProductComparedMetadata
    | ItemAddedMetadata
    | ItemRemovedMetadata
    | CartMetadata
    | DeliveryCheckedMetadata
    | CouponSearchedMetadata
    | CheckoutStepMetadata
    | PaymentFailedMetadata
    | PaymentMethodChangedMetadata
    | InterventionShownMetadata
    | InterventionOutcomeMetadata
    | OrderCompletedMetadata
    | SessionEndedMetadata
)


_METADATA_BY_TYPE: dict[EventType, type[MetadataModel]] = {
    EventType.SESSION_STARTED: SessionStartedMetadata,
    EventType.SEARCH_PERFORMED: SearchPerformedMetadata,
    EventType.PRODUCT_VIEWED: SourceMetadata,
    EventType.REVIEW_OPENED: SourceMetadata,
    EventType.REVIEW_DWELL_RECORDED: ReviewDwellMetadata,
    EventType.SIMILAR_PRODUCT_VIEWED: SimilarProductMetadata,
    EventType.PRODUCT_COMPARED: ProductComparedMetadata,
    EventType.ITEM_ADDED_TO_CART: ItemAddedMetadata,
    EventType.ITEM_REMOVED_FROM_CART: ItemRemovedMetadata,
    EventType.CART_VIEWED: CartMetadata,
    EventType.DELIVERY_CHECKED: DeliveryCheckedMetadata,
    EventType.COUPON_SEARCHED: CouponSearchedMetadata,
    EventType.CHECKOUT_STARTED: CartMetadata,
    EventType.CHECKOUT_STEP_VIEWED: CheckoutStepMetadata,
    EventType.PAYMENT_FAILED: PaymentFailedMetadata,
    EventType.PAYMENT_METHOD_CHANGED: PaymentMethodChangedMetadata,
    EventType.INTERVENTION_SHOWN: InterventionShownMetadata,
    EventType.INTERVENTION_CLICKED: InterventionOutcomeMetadata,
    EventType.INTERVENTION_DISMISSED: InterventionOutcomeMetadata,
    EventType.ORDER_COMPLETED: OrderCompletedMetadata,
    EventType.SESSION_ENDED: SessionEndedMetadata,
}

PRODUCT_EVENT_TYPES = {
    EventType.PRODUCT_VIEWED,
    EventType.REVIEW_OPENED,
    EventType.REVIEW_DWELL_RECORDED,
    EventType.SIMILAR_PRODUCT_VIEWED,
    EventType.PRODUCT_COMPARED,
    EventType.ITEM_ADDED_TO_CART,
    EventType.ITEM_REMOVED_FROM_CART,
    EventType.DELIVERY_CHECKED,
}


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: EventType
    session_id: str
    user_id: str | None = None
    product_id: str | None = None
    sequence_no: Annotated[int, Field(gt=0)]
    client_timestamp: datetime
    metadata: Metadata

    @model_validator(mode="before")
    @classmethod
    def validate_metadata_for_event(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        event_type = EventType(data.get("event_type"))
        metadata_model = _METADATA_BY_TYPE[event_type]
        data = dict(data)
        data["metadata"] = metadata_model.model_validate(data.get("metadata", {}))
        if event_type in PRODUCT_EVENT_TYPES and not data.get("product_id"):
            raise ValueError(f"product_id is required for {event_type.value}")
        return data

    @field_validator("event_id")
    @classmethod
    def require_uuid4(cls, value: UUID) -> UUID:
        if value.version != 4:
            raise ValueError("event_id must be a UUIDv4")
        return value
