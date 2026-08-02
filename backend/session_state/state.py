from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


COUNTER_DEFAULTS = {
    "product_views": 0,
    "distinct_products_viewed": 0,
    "review_opens": 0,
    "review_dwell_ms": 0,
    "similar_product_views": 0,
    "comparisons": 0,
    "cart_views": 0,
    "cart_adds": 0,
    "cart_removes": 0,
    "searches": 0,
    "price_sorts": 0,
    "coupon_searches": 0,
    "delivery_checks": 0,
    "checkout_starts": 0,
    "checkout_max_step": 0,
    "payment_failures": 0,
    "payment_method_changes": 0,
    "back_from_checkout": 0,
    "wishlist_adds": 0,
}


def _empty_cart() -> dict[str, Any]:
    return {
        "value": 0.0,
        "mrp_total": 0.0,
        "item_count": 0,
        "delivery_fee": 0.0,
        "promo_code": None,
        "items": [],
        "first_add_at": None,
    }


def _empty_interventions() -> dict[str, Any]:
    return {
        "shown": [],
        "dismissal_count": 0,
        "click_count": 0,
        "last_shown_at": None,
    }


@dataclass(slots=True)
class SessionState:
    session_id: str
    user_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_event_at: datetime | None = None
    device_type: str | None = None
    referral_source: str | None = None
    cart: dict[str, Any] = field(default_factory=_empty_cart)
    counters: dict[str, int] = field(default_factory=lambda: dict(COUNTER_DEFAULTS))
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    interventions: dict[str, Any] = field(default_factory=_empty_interventions)
    cooldowns: dict[str, str] = field(default_factory=dict)
    last_decision: dict[str, Any] | None = None
    experiment: dict[str, str] | None = None
    current_product_id: str | None = None
    current_route: str | None = None
    viewed_product_ids: set[str] = field(default_factory=set)
    order_completed: bool = False
    ended: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["last_event_at"] = self.last_event_at.isoformat() if self.last_event_at else None
        data["viewed_product_ids"] = sorted(self.viewed_product_ids)
        return data


def session_response(state: SessionState) -> dict[str, Any]:
    return {
        "session": {
            "session_id": state.session_id,
            "user_id": state.user_id,
            "started_at": state.started_at.isoformat(),
            "last_event_at": state.last_event_at.isoformat() if state.last_event_at else None,
            "device_type": state.device_type,
            "referral_source": state.referral_source,
            "current_product_id": state.current_product_id,
            "current_route": state.current_route,
            "ended": state.ended,
            "order_completed": state.order_completed,
        },
        "cart": state.cart,
        "counters": state.counters,
        "current_features": None,
        "feature_schema_version": None,
        "latest_decision": state.last_decision,
        "interventions": state.interventions,
    }
