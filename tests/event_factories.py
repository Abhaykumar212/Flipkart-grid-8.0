from datetime import datetime, timezone
from uuid import uuid4

from backend.domain.events import EventType, PRODUCT_EVENT_TYPES

DEFAULT_TIMESTAMP = datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc)

METADATA_BY_EVENT = {
    EventType.SESSION_STARTED: {"device_type": "DESKTOP", "referral_source": "DIRECT", "viewport_width": 1440},
    EventType.SEARCH_PERFORMED: {"query": "phone", "result_count": 10, "sort_order": "RELEVANCE"},
    EventType.PRODUCT_VIEWED: {"source": "DIRECT"},
    EventType.REVIEW_OPENED: {"source": "PRODUCT_PAGE"},
    EventType.REVIEW_DWELL_RECORDED: {"dwell_ms": 4200},
    EventType.SIMILAR_PRODUCT_VIEWED: {"origin_product_id": "p-1002"},
    EventType.PRODUCT_COMPARED: {"compared_with": ["p-1002", "p-1003"]},
    EventType.ITEM_ADDED_TO_CART: {"quantity": 1, "unit_price": 71999, "variant": None},
    EventType.ITEM_REMOVED_FROM_CART: {"quantity": 1},
    EventType.CART_VIEWED: {"cart_value": 71999, "item_count": 1},
    EventType.DELIVERY_CHECKED: {"pincode": "560001", "estimated_days": 2, "available": True},
    EventType.COUPON_SEARCHED: {"code": "SAVE10", "applied": True},
    EventType.CHECKOUT_STARTED: {"cart_value": 71999, "item_count": 1},
    EventType.CHECKOUT_STEP_VIEWED: {"step": 2, "step_name": "SUMMARY"},
    EventType.PAYMENT_FAILED: {"method": "CARD", "reason_code": "DECLINED", "attempt_no": 1},
    EventType.PAYMENT_METHOD_CHANGED: {"from_method": "CARD", "to_method": "UPI"},
    EventType.INTERVENTION_SHOWN: {"decision_id": "d1", "intervention_id": "NO_ACTION", "surface": "INLINE_CARD"},
    EventType.INTERVENTION_CLICKED: {"decision_id": "d1", "intervention_id": "NO_ACTION"},
    EventType.INTERVENTION_DISMISSED: {"decision_id": "d1", "intervention_id": "NO_ACTION"},
    EventType.ORDER_COMPLETED: {"order_id": "o1", "order_value": 71999, "payment_method": "UPI"},
    EventType.SESSION_ENDED: {"reason": "EXPLICIT"},
}


def event_payload(
    event_type: EventType,
    *,
    session_id: str = "s1",
    sequence_no: int = 1,
    event_id: str | None = None,
    timestamp: datetime = DEFAULT_TIMESTAMP,
) -> dict:
    payload = {
        "event_id": event_id or str(uuid4()),
        "event_type": event_type.value,
        "session_id": session_id,
        "sequence_no": sequence_no,
        "client_timestamp": timestamp.isoformat(),
        "metadata": dict(METADATA_BY_EVENT[event_type]),
    }
    if event_type in PRODUCT_EVENT_TYPES:
        payload["product_id"] = "p-1001"
    return payload
