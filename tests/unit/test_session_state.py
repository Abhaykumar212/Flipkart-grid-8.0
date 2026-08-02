from backend.domain.events import EventEnvelope, EventType
from backend.session_state.state import SessionState
from backend.session_state.updater import apply
from tests.event_factories import event_payload


def test_every_event_type_updates_state_without_mutating_input():
    state = SessionState(session_id="s1")
    original = state.to_dict()

    for sequence_no, event_type in enumerate(EventType, start=1):
        event = EventEnvelope.model_validate(
            event_payload(event_type, sequence_no=sequence_no)
        )
        updated = apply(state, event)
        assert state.to_dict() == original
        state = updated
        original = state.to_dict()

    assert state.counters == {
        "product_views": 1,
        "distinct_products_viewed": 1,
        "review_opens": 1,
        "review_dwell_ms": 4200,
        "similar_product_views": 1,
        "comparisons": 1,
        "cart_views": 1,
        "cart_adds": 1,
        "cart_removes": 1,
        "searches": 1,
        "price_sorts": 0,
        "coupon_searches": 1,
        "delivery_checks": 1,
        "checkout_starts": 1,
        "checkout_max_step": 2,
        "payment_failures": 1,
        "payment_method_changes": 1,
        "back_from_checkout": 0,
        "wishlist_adds": 0,
    }
    assert state.interventions["click_count"] == 1
    assert state.interventions["dismissal_count"] == 1
    assert len(state.interventions["shown"]) == 1
    assert state.order_completed
    assert state.ended
    assert len(state.recent_events) == 21
