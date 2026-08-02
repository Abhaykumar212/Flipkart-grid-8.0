from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from backend import config
from backend.domain.events import EventType
from backend.session_state.state import SessionState


DIRECT_TRIGGERS = {
    EventType.CART_VIEWED.value,
    EventType.ITEM_ADDED_TO_CART.value,
    EventType.CHECKOUT_STARTED.value,
    EventType.PAYMENT_FAILED.value,
    EventType.PAYMENT_METHOD_CHANGED.value,
    EventType.DELIVERY_CHECKED.value,
    EventType.COUPON_SEARCHED.value,
}
THRESHOLD_TRIGGERS = {
    EventType.REVIEW_OPENED.value: ("review_opens", 3),
    EventType.SIMILAR_PRODUCT_VIEWED.value: ("similar_product_views", 5),
    EventType.PRODUCT_COMPARED.value: ("comparisons", 2),
}
TRIGGER_NAMES = DIRECT_TRIGGERS | set(THRESHOLD_TRIGGERS) | {"PERIODIC"}
CONTINUOUS_FEATURES = {
    "c_age_seconds",
    "s_duration_seconds",
    "s_review_dwell_seconds",
    "s_idle_seconds_current",
    "s_event_velocity_per_min",
}


@dataclass(frozen=True, slots=True)
class TriggerVerdict:
    should_decide: bool
    reason: str
    feature_hash: str
    trigger_event_id: str | None = None
    retry_after_seconds: float | None = None


def material_feature_hash(features: dict[str, float]) -> str:
    material = {
        name: value
        for name, value in features.items()
        if (
            name.startswith(("c_", "d_", "pay_"))
            or (name.startswith("s_") and float(value).is_integer())
        )
        and name not in CONTINUOUS_FEATURES
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode()).hexdigest()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return _aware(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def _trigger_event(state: SessionState, trigger: str) -> dict | None:
    return next(
        (
            event
            for event in reversed(state.recent_events)
            if event.get("event_type") == trigger
        ),
        None,
    )


def evaluate(
    state: SessionState,
    trigger: str,
    features: dict[str, float],
    *,
    force: bool = False,
    now: datetime | None = None,
) -> TriggerVerdict:
    """Evaluate Phase 5 trigger gates in their frozen order."""

    evaluated_at = _aware(now or datetime.now(timezone.utc))
    feature_hash = material_feature_hash(features)
    if trigger not in TRIGGER_NAMES:
        return TriggerVerdict(False, "unsupported_trigger", feature_hash)

    event = None if trigger == "PERIODIC" else _trigger_event(state, trigger)
    event_id = str(event["event_id"]) if event and event.get("event_id") else None
    if trigger != "PERIODIC" and event is None:
        return TriggerVerdict(False, "trigger_event_not_found", feature_hash)
    threshold = THRESHOLD_TRIGGERS.get(trigger)
    if threshold and state.counters.get(threshold[0], 0) < threshold[1]:
        return TriggerVerdict(False, "trigger_threshold_not_met", feature_hash, event_id)
    if trigger == "PERIODIC" and features["c_item_count"] <= 0:
        return TriggerVerdict(False, "periodic_cart_empty", feature_hash)

    event_at = _timestamp(event.get("server_timestamp")) if event else state.last_event_at
    elapsed = (
        (evaluated_at - _aware(event_at)).total_seconds()
        if isinstance(event_at, datetime)
        else config.DECISION_DEBOUNCE_SECONDS
    )
    if elapsed < config.DECISION_DEBOUNCE_SECONDS:
        retry = round(config.DECISION_DEBOUNCE_SECONDS - elapsed, 3)
        return TriggerVerdict(False, "debounce_active", feature_hash, event_id, retry)

    last = state.last_decision or {}
    decided_at = _timestamp(last.get("at") or last.get("decided_at"))
    if decided_at and not force and trigger != EventType.PAYMENT_FAILED.value:
        since_decision = (evaluated_at - decided_at).total_seconds()
        if since_decision < config.MIN_DECISION_INTERVAL_SECONDS:
            retry = round(config.MIN_DECISION_INTERVAL_SECONDS - since_decision, 3)
            return TriggerVerdict(
                False, "minimum_interval_active", feature_hash, event_id, retry
            )
    if (last.get("feature_hash") or last.get("material_feature_hash")) == feature_hash:
        return TriggerVerdict(False, "material_features_unchanged", feature_hash, event_id)
    if state.ended or state.order_completed:
        return TriggerVerdict(False, "session_terminated", feature_hash, event_id)
    if event and event.get("is_late") is True:
        return TriggerVerdict(False, "late_event", feature_hash, event_id)
    return TriggerVerdict(True, "trigger_accepted", feature_hash, event_id)
