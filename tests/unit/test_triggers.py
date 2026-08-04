from datetime import datetime, timedelta, timezone

from backend.domain.events import EventType
from backend.feature_engine.schema import FEATURE_SCHEMA_V1
from backend.orchestrator.triggers import evaluate, material_feature_hash
from backend.session_state.state import SessionState


NOW = datetime(2026, 8, 2, 12, tzinfo=timezone.utc)


def _features() -> dict[str, float]:
    return {item.name: float(item.default) for item in FEATURE_SCHEMA_V1}


def _state(*, seconds_ago: float = 4, late: bool = False) -> SessionState:
    state = SessionState(session_id="s1")
    state.recent_events = [{
        "event_id": "e1",
        "event_type": EventType.CART_VIEWED.value,
        "server_timestamp": (NOW - timedelta(seconds=seconds_ago)).isoformat(),
        "is_late": late,
    }]
    return state


def test_debounce_then_accepts_trigger():
    assert evaluate(_state(seconds_ago=1), "CART_VIEWED", _features(), now=NOW).reason == "debounce_active"
    assert evaluate(_state(), "CART_VIEWED", _features(), now=NOW).should_decide


def test_minimum_interval_and_force_bypass():
    state = _state()
    state.last_decision = {
        "at": (NOW - timedelta(seconds=5)).isoformat(),
        "feature_hash": "different",
    }
    assert evaluate(state, "CART_VIEWED", _features(), now=NOW).reason == "minimum_interval_active"
    assert evaluate(state, "CART_VIEWED", _features(), force=True, now=NOW).should_decide


def test_material_hash_ignores_ticking_features_but_not_counts():
    first = _features()
    second = dict(first)
    second.update({
        "s_duration_seconds": 90,
        "c_age_seconds": 90,
        # Within the same dwell bucket, so it must not move the hash.
        "s_review_dwell_seconds": 9,
        "s_idle_seconds_current": 10,
        "s_event_velocity_per_min": 4,
    })
    assert material_feature_hash(first) == material_feature_hash(second)
    second["s_review_open_count"] = 3
    assert material_feature_hash(first) != material_feature_hash(second)


def test_material_hash_tracks_sustained_review_dwell():
    """Dwell is the whole signal for a browsing shopper, so a sustained read has
    to register as a new situation even though the value ticks continuously."""
    first = _features()
    same_bucket = dict(first, s_review_dwell_seconds=9)
    later_bucket = dict(first, s_review_dwell_seconds=45)
    assert material_feature_hash(first) == material_feature_hash(same_bucket)
    assert material_feature_hash(first) != material_feature_hash(later_bucket)


def test_threshold_late_and_terminated_gates():
    review = _state()
    review.recent_events[0]["event_type"] = EventType.REVIEW_OPENED.value
    review.counters["review_opens"] = 1
    assert evaluate(review, "REVIEW_OPENED", _features(), now=NOW).reason == "trigger_threshold_not_met"
    review.counters["review_opens"] = 2
    review.recent_events[0]["is_late"] = True
    assert evaluate(review, "REVIEW_OPENED", _features(), now=NOW).reason == "late_event"
    review.recent_events[0]["is_late"] = False
    review.ended = True
    assert evaluate(review, "REVIEW_OPENED", _features(), now=NOW).reason == "session_terminated"
