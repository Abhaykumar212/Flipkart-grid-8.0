from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from backend.domain.events import EventEnvelope, EventType

from .state import SessionState


def _metadata(event: EventEnvelope) -> dict[str, Any]:
    return event.metadata.model_dump(mode="json")


def _update_cart_add(state: SessionState, event: EventEnvelope, at: datetime) -> None:
    metadata = _metadata(event)
    variant = metadata.get("variant")
    existing = next(
        (
            item
            for item in state.cart["items"]
            if item["product_id"] == event.product_id and item.get("variant") == variant
        ),
        None,
    )
    if existing:
        existing["quantity"] += metadata["quantity"]
    else:
        state.cart["items"].append({
            "product_id": event.product_id,
            "quantity": metadata["quantity"],
            "unit_price": metadata["unit_price"],
            "variant": variant,
            "added_at": at.isoformat(),
        })
    state.cart["item_count"] = sum(item["quantity"] for item in state.cart["items"])
    state.cart["value"] = sum(item["quantity"] * item["unit_price"] for item in state.cart["items"])
    if state.cart["first_add_at"] is None:
        state.cart["first_add_at"] = at.isoformat()


def _update_cart_remove(state: SessionState, event: EventEnvelope) -> None:
    quantity = _metadata(event)["quantity"]
    for item in state.cart["items"]:
        if item["product_id"] == event.product_id:
            item["quantity"] -= quantity
            break
    state.cart["items"] = [item for item in state.cart["items"] if item["quantity"] > 0]
    state.cart["item_count"] = sum(item["quantity"] for item in state.cart["items"])
    state.cart["value"] = sum(item["quantity"] * item["unit_price"] for item in state.cart["items"])


def apply(
    state: SessionState,
    event: EventEnvelope,
    *,
    server_timestamp: datetime | None = None,
) -> SessionState:
    """Return a new state with one event applied; no I/O and no input mutation."""
    updated = deepcopy(state)
    event_time = server_timestamp or datetime.now(timezone.utc)
    metadata = _metadata(event)
    updated.last_event_at = event_time
    updated.recent_events.append({
        **event.model_dump(mode="json"),
        "server_timestamp": event_time.isoformat(),
    })
    updated.recent_events = updated.recent_events[-50:]

    if event.event_type == EventType.SESSION_STARTED:
        updated.user_id = event.user_id
        updated.started_at = event.client_timestamp
        updated.device_type = metadata["device_type"]
        updated.referral_source = metadata["referral_source"]
        updated.current_route = "/"
    elif event.event_type == EventType.SEARCH_PERFORMED:
        updated.counters["searches"] += 1
        if "PRICE" in metadata["sort_order"].upper():
            updated.counters["price_sorts"] += 1
        updated.current_route = "/search"
    elif event.event_type == EventType.PRODUCT_VIEWED:
        updated.counters["product_views"] += 1
        updated.viewed_product_ids.add(event.product_id)
        updated.counters["distinct_products_viewed"] = len(updated.viewed_product_ids)
        updated.current_product_id = event.product_id
        updated.current_route = f"/product/{event.product_id}"
    elif event.event_type == EventType.REVIEW_OPENED:
        updated.counters["review_opens"] += 1
    elif event.event_type == EventType.REVIEW_DWELL_RECORDED:
        updated.counters["review_dwell_ms"] += metadata["dwell_ms"]
    elif event.event_type == EventType.SIMILAR_PRODUCT_VIEWED:
        updated.counters["similar_product_views"] += 1
        updated.current_product_id = event.product_id
    elif event.event_type == EventType.PRODUCT_COMPARED:
        updated.counters["comparisons"] += 1
    elif event.event_type == EventType.ITEM_ADDED_TO_CART:
        updated.counters["cart_adds"] += 1
        _update_cart_add(updated, event, event_time)
    elif event.event_type == EventType.ITEM_REMOVED_FROM_CART:
        updated.counters["cart_removes"] += 1
        _update_cart_remove(updated, event)
    elif event.event_type == EventType.CART_VIEWED:
        updated.counters["cart_views"] += 1
        updated.cart["value"] = metadata["cart_value"]
        updated.cart["item_count"] = metadata["item_count"]
        updated.current_route = "/cart"
    elif event.event_type == EventType.DELIVERY_CHECKED:
        updated.counters["delivery_checks"] += 1
    elif event.event_type == EventType.COUPON_SEARCHED:
        updated.counters["coupon_searches"] += 1
        if metadata["applied"]:
            updated.cart["promo_code"] = metadata.get("code")
    elif event.event_type == EventType.CHECKOUT_STARTED:
        updated.counters["checkout_starts"] += 1
        updated.cart["value"] = metadata["cart_value"]
        updated.cart["item_count"] = metadata["item_count"]
        updated.current_route = "/checkout"
    elif event.event_type == EventType.CHECKOUT_STEP_VIEWED:
        updated.counters["checkout_max_step"] = max(
            updated.counters["checkout_max_step"], metadata["step"]
        )
        updated.current_route = "/checkout"
    elif event.event_type == EventType.PAYMENT_FAILED:
        updated.counters["payment_failures"] += 1
    elif event.event_type == EventType.PAYMENT_METHOD_CHANGED:
        updated.counters["payment_method_changes"] += 1
    elif event.event_type == EventType.INTERVENTION_SHOWN:
        updated.interventions["shown"].append({
            "decision_id": metadata["decision_id"],
            "intervention_id": metadata["intervention_id"],
            "surface": metadata["surface"],
            "shown_at": event_time.isoformat(),
            "outcome": "SHOWN",
        })
        updated.interventions["last_shown_at"] = event_time.isoformat()
    elif event.event_type == EventType.INTERVENTION_CLICKED:
        updated.interventions["click_count"] += 1
        for shown in reversed(updated.interventions["shown"]):
            if (
                shown["decision_id"] == metadata["decision_id"]
                and shown["intervention_id"] == metadata["intervention_id"]
            ):
                shown["outcome"] = "CLICKED"
                break
    elif event.event_type == EventType.INTERVENTION_DISMISSED:
        updated.interventions["dismissal_count"] += 1
        for shown in reversed(updated.interventions["shown"]):
            if (
                shown["decision_id"] == metadata["decision_id"]
                and shown["intervention_id"] == metadata["intervention_id"]
            ):
                shown["outcome"] = "DISMISSED"
                break
    elif event.event_type == EventType.ORDER_COMPLETED:
        updated.order_completed = True
    elif event.event_type == EventType.SESSION_ENDED:
        updated.ended = True

    return updated
