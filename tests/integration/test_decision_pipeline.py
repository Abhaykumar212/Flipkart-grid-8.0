from datetime import datetime, timezone

from sqlalchemy import func, select

from backend.domain.events import EventType
from backend.storage.models import DecisionTrace, ModelPrediction, SessionFeatureSnapshot
from backend.orchestrator.pipeline import run_decision
from backend.session_state.cache import cache_session_state
from backend.session_state.state import SessionState
from tests.event_factories import event_payload


def _create_session(api_harness, session_id: str) -> None:
    response = api_harness.client.post(
        "/api/v1/sessions",
        json={"session_id": session_id, "device_type": "DESKTOP", "referral_source": "DIRECT"},
    )
    assert response.status_code == 201, response.text


def _emit(api_harness, event_type: EventType, session_id: str, sequence_no: int) -> dict:
    payload = event_payload(
        event_type,
        session_id=session_id,
        sequence_no=sequence_no,
        timestamp=datetime.now(timezone.utc),
    )
    response = api_harness.client.post("/api/v1/events", json=payload)
    assert response.status_code == 202, response.text
    return payload


def _emit_low_value_cart(api_harness, session_id: str, sequence_no: int) -> None:
    payload = event_payload(
        EventType.ITEM_ADDED_TO_CART,
        session_id=session_id,
        sequence_no=sequence_no,
        timestamp=datetime.now(timezone.utc),
    )
    payload["product_id"] = "p-1006"
    payload["metadata"]["unit_price"] = 8_499
    response = api_harness.client.post("/api/v1/events", json=payload)
    assert response.status_code == 202, response.text


def _emit_intervention(
    api_harness,
    event_type: EventType,
    session_id: str,
    sequence_no: int,
    decision_id: str,
    intervention_id: str,
) -> None:
    payload = event_payload(event_type, session_id=session_id, sequence_no=sequence_no, timestamp=datetime.now(timezone.utc))
    payload["metadata"] = {
        "decision_id": decision_id,
        "intervention_id": intervention_id,
        **({"surface": "INLINE_CARD"} if event_type == EventType.INTERVENTION_SHOWN else {}),
    }
    response = api_harness.client.post("/api/v1/events", json=payload)
    assert response.status_code == 202, response.text


def test_low_risk_decision_is_explained_and_persisted_atomically(api_harness, monkeypatch):
    monkeypatch.setattr("backend.config.DECISION_DEBOUNCE_SECONDS", 0)
    session_id = "decision-low-risk"
    _create_session(api_harness, session_id)
    trigger = _emit(api_harness, EventType.CART_VIEWED, session_id, 1)

    response = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        json={"trigger": "CART_VIEWED", "force": False},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"] == "NO_ACTION"
    assert body["recommended_intervention"]["type"] == "NO_ACTION"
    assert body["abandonment_probability"] < 0.4
    assert body["explanation"]["risk"]["statement"]

    with api_harness.sessions() as db:
        trace = db.get(DecisionTrace, body["decision_id"])
        assert trace is not None
        snapshot = db.get(SessionFeatureSnapshot, trace.feature_snapshot_id)
        assert snapshot is not None and snapshot.trigger_event_id == trigger["event_id"]
        assert db.scalar(select(func.count()).select_from(ModelPrediction).where(ModelPrediction.decision_id == body["decision_id"])) == 2


def test_payment_failure_authorizes_only_backend_identified_intervention(api_harness, monkeypatch):
    monkeypatch.setattr("backend.config.DECISION_DEBOUNCE_SECONDS", 0)
    session_id = "decision-payment"
    _create_session(api_harness, session_id)
    _emit_low_value_cart(api_harness, session_id, 1)
    _emit(api_harness, EventType.CHECKOUT_STARTED, session_id, 2)
    _emit(api_harness, EventType.CHECKOUT_STEP_VIEWED, session_id, 3)
    _emit(api_harness, EventType.PAYMENT_FAILED, session_id, 4)

    response = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        json={"trigger": "PAYMENT_FAILED", "force": False},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"] == "INTERVENE", body
    assert body["recommended_intervention"]["decision_id"] == body["decision_id"]
    assert body["recommended_intervention"]["type"] in {
        "ALTERNATE_PAYMENT_METHOD", "CHECKOUT_ASSISTANCE",
    }
    assert all("status" in item and "reasons" in item for item in body["policy_results"])

    latest = api_harness.client.get(f"/api/v1/sessions/{session_id}/interventions/latest")
    assert latest.status_code == 200
    assert latest.json()["decision_id"] == body["decision_id"]
    api_harness.store.delete(f"session:{session_id}:state")
    recovered = api_harness.client.get(f"/api/v1/sessions/{session_id}/interventions/latest")
    assert recovered.status_code == 200
    assert recovered.json()["decision_id"] == body["decision_id"]


def test_two_dismissals_suppress_all_further_customer_actions(api_harness, monkeypatch):
    monkeypatch.setattr("backend.config.DECISION_DEBOUNCE_SECONDS", 0)
    monkeypatch.setattr("backend.config.MIN_DECISION_INTERVAL_SECONDS", 0)
    session_id = "decision-fatigue-treatment"
    _create_session(api_harness, session_id)
    _emit_low_value_cart(api_harness, session_id, 1)
    for sequence in range(2, 5):
        _emit(api_harness, EventType.REVIEW_OPENED, session_id, sequence)
    for sequence in range(5, 10):
        _emit(api_harness, EventType.SIMILAR_PRODUCT_VIEWED, session_id, sequence)
    first = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        json={"trigger": "SIMILAR_PRODUCT_VIEWED", "force": True},
    ).json()
    assert first["decision"] == "INTERVENE"
    first_type = first["recommended_intervention"]["type"]
    _emit_intervention(api_harness, EventType.INTERVENTION_SHOWN, session_id, 10, first["decision_id"], first_type)
    _emit_intervention(api_harness, EventType.INTERVENTION_DISMISSED, session_id, 11, first["decision_id"], first_type)

    _emit(api_harness, EventType.CHECKOUT_STARTED, session_id, 12)
    _emit(api_harness, EventType.CHECKOUT_STEP_VIEWED, session_id, 13)
    _emit(api_harness, EventType.PAYMENT_FAILED, session_id, 14)
    second = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        json={"trigger": "PAYMENT_FAILED", "force": True},
    ).json()
    assert second["decision"] == "INTERVENE", second
    second_type = second["recommended_intervention"]["type"]
    _emit_intervention(api_harness, EventType.INTERVENTION_SHOWN, session_id, 15, second["decision_id"], second_type)
    _emit_intervention(api_harness, EventType.INTERVENTION_DISMISSED, session_id, 16, second["decision_id"], second_type)

    _emit(api_harness, EventType.DELIVERY_CHECKED, session_id, 17)
    third = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        json={"trigger": "DELIVERY_CHECKED", "force": True},
    ).json()
    assert third["decision"] == "NO_ACTION"
    rejected = [item for item in third["policy_results"] if item["intervention"] != "NO_ACTION"]
    assert rejected
    assert all(item["reasons"] == ["repeated_dismissals"] for item in rejected)


def test_pipeline_is_deterministic_for_100_runs_and_p95_is_under_budget(api_harness, monkeypatch):
    monkeypatch.setattr("backend.config.DECISION_DEBOUNCE_SECONDS", 0)
    session_id = "decision-determinism"
    _create_session(api_harness, session_id)
    _emit_low_value_cart(api_harness, session_id, 1)
    for sequence in range(2, 5):
        _emit(api_harness, EventType.REVIEW_OPENED, session_id, sequence)
    for sequence in range(5, 10):
        _emit(api_harness, EventType.SIMILAR_PRODUCT_VIEWED, session_id, sequence)

    outcomes = []
    latencies = []
    decided_at = datetime.now(timezone.utc)
    with api_harness.sessions() as db:
        for _ in range(100):
            state = api_harness.store.get(f"session:{session_id}:state")
            assert isinstance(state, SessionState)
            state.last_decision = None
            cache_session_state(api_harness.store, state)
            run = run_decision(
                session_id,
                "SIMILAR_PRODUCT_VIEWED",
                db,
                api_harness.store,
                force=True,
                now=decided_at,
            )
            recommended = run.response["recommended_intervention"]
            assert isinstance(recommended, dict)
            outcomes.append((run.response["decision"], recommended["type"], run.response["risk_level"]))
            latency = run.response["latency_ms"]
            assert isinstance(latency, dict)
            latencies.append(float(latency["total"]))
    assert len(set(outcomes)) == 1
    assert outcomes[0][0] == "INTERVENE"
    assert sorted(latencies)[94] < 300
