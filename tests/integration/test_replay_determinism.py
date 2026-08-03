from datetime import datetime, timezone

from backend.domain.events import EventType
from scripts import replay_session
from tests.event_factories import event_payload


def test_replay_reproduces_the_original_intervention_and_score(api_harness, monkeypatch) -> None:
    monkeypatch.setattr("backend.config.DECISION_DEBOUNCE_SECONDS", 0)
    session_id = "replay-treatment"
    assert api_harness.client.post("/api/v1/sessions", json={"session_id": session_id}).status_code == 201
    for sequence, event_type in enumerate(
        (EventType.ITEM_ADDED_TO_CART, EventType.CHECKOUT_STARTED, EventType.PAYMENT_FAILED),
        start=1,
    ):
        payload = event_payload(
            event_type,
            session_id=session_id,
            sequence_no=sequence,
            timestamp=datetime.now(timezone.utc),
        )
        if event_type is EventType.ITEM_ADDED_TO_CART:
            payload["product_id"] = "p-1006"
            payload["metadata"]["unit_price"] = 8_499
        assert api_harness.client.post("/api/v1/events", json=payload).status_code == 202
    decision = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        json={"trigger": "PAYMENT_FAILED", "force": True},
    )
    assert decision.status_code == 200, decision.text

    monkeypatch.setattr(replay_session, "SessionLocal", api_harness.sessions)
    result = replay_session.replay(session_id)
    assert result["matches"] is True
    assert result["original_intervention"] == result["replayed_intervention"]
    assert result["original_score"] == result["replayed_score"]
