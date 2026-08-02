from datetime import datetime, timezone

from sqlalchemy import func, select

from backend.domain.events import EventType
from backend.storage.models import DecisionTrace, Event
from tests.event_factories import event_payload


def _create_session(api_harness, session_id: str) -> None:
    response = api_harness.client.post(
        "/api/v1/sessions",
        json={"session_id": session_id, "device_type": "DESKTOP", "referral_source": "DIRECT"},
    )
    assert response.status_code == 201, response.text


def _create_decision(api_harness, session_id: str) -> None:
    with api_harness.sessions.begin() as db:
        db.add(DecisionTrace(
            decision_id="d1",
            session_id=session_id,
            trace_id="tr1",
            decision_time=datetime.now(timezone.utc),
            trigger="integration-test",
            model_versions={},
            abandonment_probability=0.1,
            risk_band="LOW",
            root_causes=[],
            candidate_interventions=[],
            policy_results=[],
            utility_scores=[],
            selected_intervention="NO_ACTION",
            channel=None,
            recommendation_confidence=1.0,
            decision="NO_ACTION",
            explanation={},
            latency_ms={},
        ))


def test_all_event_types_persist_and_terminal_session_rejects_more_events(api_harness):
    session_id = "s-all-events"
    _create_session(api_harness, session_id)
    _create_decision(api_harness, session_id)
    events = [
        event_payload(event_type, session_id=session_id, sequence_no=index)
        for index, event_type in enumerate(EventType, start=1)
    ]

    response = api_harness.client.post("/api/v1/events", json={"events": events})

    assert response.status_code == 202, response.text
    assert response.json()["accepted"] == len(EventType)
    with api_harness.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Event)) == len(EventType)
        assert set(db.scalars(select(Event.event_type))) == {event_type.value for event_type in EventType}

    session_response = api_harness.client.get(f"/api/v1/sessions/{session_id}")
    assert session_response.status_code == 200
    assert session_response.json()["session"]["ended"] is True

    after_end = event_payload(
        EventType.SEARCH_PERFORMED,
        session_id=session_id,
        sequence_no=len(EventType) + 1,
    )
    rejected = api_harness.client.post("/api/v1/events", json=after_end)
    assert rejected.status_code == 409
    assert rejected.headers["content-type"].startswith("application/problem+json")


def test_invalid_metadata_returns_problem_detail_with_field_path(api_harness):
    session_id = "s-invalid-metadata"
    _create_session(api_harness, session_id)
    payload = event_payload(EventType.DELIVERY_CHECKED, session_id=session_id)
    payload["metadata"]["pincode"] = "invalid"

    response = api_harness.client.post("/api/v1/events", json=payload)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert any(error["loc"][-2:] == ["metadata", "pincode"] for error in response.json()["errors"])


def test_unknown_session_and_oversized_batch_return_documented_errors(api_harness):
    unknown = api_harness.client.post(
        "/api/v1/events",
        json=event_payload(EventType.SEARCH_PERFORMED, session_id="missing"),
    )
    assert unknown.status_code == 404
    assert unknown.headers["content-type"].startswith("application/problem+json")

    batch = {
        "events": [
            event_payload(EventType.SEARCH_PERFORMED, session_id="missing", sequence_no=index)
            for index in range(1, 52)
        ]
    }
    oversized = api_harness.client.post("/api/v1/events", json=batch)
    assert oversized.status_code == 413


def test_cart_add_after_completed_order_is_rejected(api_harness):
    session_id = "s-completed-order"
    _create_session(api_harness, session_id)
    completed = api_harness.client.post(
        "/api/v1/events",
        json=event_payload(EventType.ORDER_COMPLETED, session_id=session_id),
    )
    assert completed.status_code == 202

    cart_add = event_payload(EventType.ITEM_ADDED_TO_CART, session_id=session_id, sequence_no=2)
    rejected = api_harness.client.post("/api/v1/events", json=cart_add)
    assert rejected.status_code == 409


def test_session_started_event_can_create_the_session(api_harness):
    session_id = "s-started-by-event"
    started = api_harness.client.post(
        "/api/v1/events",
        json=event_payload(EventType.SESSION_STARTED, session_id=session_id),
    )
    assert started.status_code == 202, started.text
    assert started.json()["accepted"] == 1

    session = api_harness.client.get(f"/api/v1/sessions/{session_id}")
    assert session.status_code == 200
    assert session.json()["session"]["device_type"] == "DESKTOP"
    assert session.json()["session"]["referral_source"] == "DIRECT"


def test_batch_reference_failure_rolls_back_every_event(api_harness):
    session_id = "s-atomic-batch"
    _create_session(api_harness, session_id)
    first = event_payload(EventType.SEARCH_PERFORMED, session_id=session_id, sequence_no=1)
    invalid = event_payload(EventType.PRODUCT_VIEWED, session_id=session_id, sequence_no=2)
    invalid["product_id"] = "missing-product"

    response = api_harness.client.post(
        "/api/v1/events",
        json={"events": [first, invalid]},
    )

    assert response.status_code == 404
    with api_harness.sessions() as db:
        count = db.scalar(
            select(func.count()).select_from(Event).where(Event.session_id == session_id)
        )
    assert count == 0
    state = api_harness.client.get(f"/api/v1/sessions/{session_id}").json()
    assert state["counters"]["searches"] == 0
