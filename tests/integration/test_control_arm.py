from datetime import datetime, timezone

from backend.domain.events import EventType
from tests.event_factories import event_payload


def test_control_arm_is_complete_and_never_emits_a_discount(api_harness, monkeypatch) -> None:
    monkeypatch.setattr("backend.config.DECISION_DEBOUNCE_SECONDS", 0)
    session_id = "decision-fatigue"
    assert api_harness.client.post("/api/v1/sessions", json={"session_id": session_id}).status_code == 201
    add = event_payload(
        EventType.ITEM_ADDED_TO_CART,
        session_id=session_id,
        sequence_no=1,
        timestamp=datetime.now(timezone.utc),
    )
    add["product_id"] = "p-1006"
    add["metadata"]["unit_price"] = 8_499
    assert api_harness.client.post("/api/v1/events", json=add).status_code == 202

    response = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        json={"trigger": "ITEM_ADDED_TO_CART", "force": True},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["experiment_group"] == "CONTROL"
    assert body["decision"] == "INTERVENE"
    assert body["recommended_intervention"]["type"] == "WISHLIST_REMINDER"
    assert body["recommended_intervention"]["type"] != "LIMITED_TIME_DISCOUNT"
    assert body["explanation"]["versions"]["root_cause"] == "control-skipped-v1"
