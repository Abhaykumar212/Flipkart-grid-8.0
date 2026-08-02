from datetime import datetime, timezone

from backend.dashboard_api.stream import broadcaster
from backend.domain.events import EventType
from tests.event_factories import event_payload


def _create_session(api_harness, session_id: str) -> None:
    response = api_harness.client.post(
        "/api/v1/sessions",
        json={
            "session_id": session_id,
            "device_type": "DESKTOP",
            "referral_source": "DIRECT",
        },
    )
    assert response.status_code == 201, response.text


def _emit(api_harness, event_type: EventType, session_id: str, sequence_no: int) -> None:
    payload = event_payload(
        event_type,
        session_id=session_id,
        sequence_no=sequence_no,
        timestamp=datetime.now(timezone.utc),
    )
    if event_type == EventType.ITEM_ADDED_TO_CART:
        payload["product_id"] = "p-1006"
        payload["metadata"]["unit_price"] = 8_499
    response = api_harness.client.post("/api/v1/events", json=payload)
    assert response.status_code == 202, response.text


def test_dashboard_exposes_live_session_detail_and_full_decision_trace(
    api_harness, monkeypatch
) -> None:
    broadcaster.reset()
    monkeypatch.setattr("backend.config.DECISION_DEBOUNCE_SECONDS", 0)
    session_id = "dashboard-payment"
    _create_session(api_harness, session_id)
    _emit(api_harness, EventType.ITEM_ADDED_TO_CART, session_id, 1)
    _emit(api_harness, EventType.CHECKOUT_STARTED, session_id, 2)
    _emit(api_harness, EventType.CHECKOUT_STEP_VIEWED, session_id, 3)
    _emit(api_harness, EventType.PAYMENT_FAILED, session_id, 4)

    decision_response = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        json={"trigger": "PAYMENT_FAILED", "force": False},
    )
    assert decision_response.status_code == 200, decision_response.text
    decision = decision_response.json()

    sessions_response = api_harness.client.get("/api/v1/dashboard/sessions")
    assert sessions_response.status_code == 200, sessions_response.text
    sessions = sessions_response.json()
    assert sessions["count"] == 1
    row = sessions["sessions"][0]
    assert row["session_id"] == session_id
    assert row["latest_decision"]["decision_id"] == decision["decision_id"]

    detail_response = api_harness.client.get(
        f"/api/v1/dashboard/sessions/{session_id}"
    )
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert len(detail["timeline"]) == 4
    assert detail["cart"]["items"][0]["title"]
    assert len(detail["feature_snapshot"]["features"]) == 67
    assert detail["decisions"][0]["decision_id"] == decision["decision_id"]

    trace_response = api_harness.client.get(
        f"/api/v1/dashboard/decisions/{decision['decision_id']}"
    )
    assert trace_response.status_code == 200, trace_response.text
    trace = trace_response.json()
    assert trace["risk"]["probability"] == decision["abandonment_probability"]
    assert trace["root_causes"]
    assert trace["candidates"]
    assert all("policy_status" in item for item in trace["candidates"])
    assert all(
        abs(sum(item["score_breakdown"].values()) - item["score"]) <= 0.001
        for item in trace["utility_scores"]
    )
    assert set(trace["audit_answers"]) == {
        "elevated_risk",
        "root_cause",
        "selected_intervention",
        "rejected_interventions",
        "discount_not_offered",
        "uncertainty",
        "versions",
    }
    assert "discount" in trace["audit_answers"]["discount_not_offered"].lower()
    assert any(
        item["intervention"] == "LIMITED_TIME_DISCOUNT"
        and item["policy_reasons"]
        for item in trace["candidates"]
    )


def test_dashboard_returns_problem_details_for_unknown_resources(api_harness) -> None:
    session_response = api_harness.client.get("/api/v1/dashboard/sessions/missing")
    decision_response = api_harness.client.get("/api/v1/dashboard/decisions/missing")
    assert session_response.status_code == 404
    assert session_response.headers["content-type"].startswith("application/problem+json")
    assert decision_response.status_code == 404
