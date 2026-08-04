from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


Identifier = Annotated[str, Field(min_length=1, max_length=128)]
ShortText = Annotated[str, Field(min_length=1, max_length=200)]


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
    # Before SESSION_ENDED: that one is terminal, and anything declared after it
    # lands after it in any full-enum replay, where it is correctly rejected.
    EXIT_INTENT_DETECTED = "EXIT_INTENT_DETECTED"
    SESSION_ENDED = "SESSION_ENDED"


class MetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionStartedMetadata(MetadataModel):
    device_type: Literal["MOBILE", "DESKTOP"]
    referral_source: ShortText
    viewport_width: Annotated[int, Field(gt=0)]


class SearchPerformedMetadata(MetadataModel):
    query: Annotated[str, Field(min_length=1, max_length=500)]
    result_count: Annotated[int, Field(ge=0)]
    sort_order: ShortText


class ProductSourceMetadata(MetadataModel):
    source: Literal["SEARCH", "RAIL", "CATEGORY", "DIRECT"]


class ReviewSourceMetadata(MetadataModel):
    source: ShortText


class ReviewDwellMetadata(MetadataModel):
    dwell_ms: Annotated[int, Field(ge=0)]


class SimilarProductMetadata(MetadataModel):
    origin_product_id: Identifier


class ProductComparedMetadata(MetadataModel):
    compared_with: Annotated[list[Identifier], Field(min_length=1, max_length=20)]


class ItemAddedMetadata(MetadataModel):
    quantity: Annotated[int, Field(gt=0)]
    unit_price: Annotated[float, Field(gt=0)]
    variant: Annotated[str, Field(min_length=1, max_length=128)] | None = None


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
    code: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    applied: bool


class CheckoutStepMetadata(MetadataModel):
    step: Annotated[int, Field(ge=1, le=3)]
    step_name: ShortText


class PaymentFailedMetadata(MetadataModel):
    method: ShortText
    reason_code: ShortText
    attempt_no: Annotated[int, Field(gt=0)]


class PaymentMethodChangedMetadata(MetadataModel):
    from_method: ShortText
    to_method: ShortText


class InterventionShownMetadata(MetadataModel):
    decision_id: Identifier
    intervention_id: Identifier
    surface: ShortText


class InterventionOutcomeMetadata(MetadataModel):
    decision_id: Identifier
    intervention_id: Identifier


class OrderCompletedMetadata(MetadataModel):
    order_id: Identifier
    order_value: Annotated[float, Field(gt=0)]
    payment_method: ShortText


class SessionEndedMetadata(MetadataModel):
    reason: Literal["EXPLICIT", "TIMEOUT", "UNLOAD"]


class ExitIntentMetadata(MetadataModel):
    #: How the shopper signalled they were leaving. POINTER_EXIT is the cursor
    #: heading for the browser chrome; TAB_HIDDEN is a background tab.
    signal: Literal["POINTER_EXIT", "TAB_HIDDEN"]


Metadata = (
    SessionStartedMetadata
    | SearchPerformedMetadata
    | ProductSourceMetadata
    | ReviewSourceMetadata
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
    | ExitIntentMetadata
)


_METADATA_BY_TYPE: dict[EventType, type[MetadataModel]] = {
    EventType.SESSION_STARTED: SessionStartedMetadata,
    EventType.SEARCH_PERFORMED: SearchPerformedMetadata,
    EventType.PRODUCT_VIEWED: ProductSourceMetadata,
    EventType.REVIEW_OPENED: ReviewSourceMetadata,
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
    EventType.EXIT_INTENT_DETECTED: ExitIntentMetadata,
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
    session_id: Identifier
    user_id: Identifier | None = None
    product_id: Identifier | None = None
    sequence_no: Annotated[int, Field(gt=0)]
    client_timestamp: datetime
    metadata: Metadata

    @model_validator(mode="before")
    @classmethod
    def validate_metadata_for_event(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw_event_type = data.get("event_type")
        try:
            event_type = EventType(raw_event_type)
        except (TypeError, ValueError) as error:
            value_error = ValueError(f"Unknown event_type: {raw_event_type!r}")
            raise ValidationError.from_exception_data(cls.__name__, [{
                "type": "value_error",
                "loc": ("event_type",),
                "input": raw_event_type,
                "ctx": {"error": value_error},
            }]) from error
        metadata_model = _METADATA_BY_TYPE[event_type]
        data = dict(data)
        try:
            data["metadata"] = metadata_model.model_validate(data.get("metadata", {}))
        except ValidationError as error:
            errors = [
                {**item, "loc": ("metadata", *item["loc"])}
                for item in error.errors()
            ]
            raise ValidationError.from_exception_data(cls.__name__, errors) from error
        if event_type in PRODUCT_EVENT_TYPES and not data.get("product_id"):
            value_error = ValueError(f"product_id is required for {event_type.value}")
            raise ValidationError.from_exception_data(cls.__name__, [{
                "type": "value_error",
                "loc": ("product_id",),
                "input": data.get("product_id"),
                "ctx": {"error": value_error},
            }])
        return data

    @field_validator("event_id")
    @classmethod
    def require_uuid4(cls, value: UUID) -> UUID:
        if value.version != 4:
            raise ValueError("event_id must be a UUIDv4")
        return value

    @field_validator("client_timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("client_timestamp must include a timezone")
        return value
