from datetime import datetime, timezone

from backend.domain.events import EventType
from backend.observability.rate_limit import (
    decision_rate_limiter,
    event_rate_limiter,
)
from tests.event_factories import event_payload


def _create(api_harness, session_id: str) -> None:
    response = api_harness.client.post(
        "/api/v1/sessions",
        json={"session_id": session_id},
    )
    assert response.status_code == 201


def test_runtime_metrics_and_event_rate_limit(api_harness, monkeypatch):
    event_rate_limiter.reset()
    monkeypatch.setattr("backend.config.EVENT_RATE_LIMIT_PER_MINUTE", 1)
    session_id = "observability-event-limit"
    _create(api_harness, session_id)
    first = event_payload(
        EventType.CART_VIEWED,
        session_id=session_id,
        sequence_no=1,
        timestamp=datetime.now(timezone.utc),
    )
    second = event_payload(
        EventType.CART_VIEWED,
        session_id=session_id,
        sequence_no=2,
        timestamp=datetime.now(timezone.utc),
    )
    assert api_harness.client.post("/api/v1/events", json=first).status_code == 202
    rejected = api_harness.client.post("/api/v1/events", json=second)
    assert rejected.status_code == 429
    assert int(rejected.headers["retry-after"]) > 0

    metrics = api_harness.client.get("/api/v1/metrics")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["counters"]["events_ingested"]["total"] >= 1
    assert "event_ingest" in body["latency_ms"]
    assert body["drift"]["automated_action"] is False


def test_decision_rate_limit_and_hindi_response(api_harness, monkeypatch):
    decision_rate_limiter.reset()
    monkeypatch.setattr("backend.config.DECISION_RATE_LIMIT_PER_MINUTE", 1)
    monkeypatch.setattr("backend.config.DECISION_DEBOUNCE_SECONDS", 0)
    session_id = "observability-decision-limit"
    _create(api_harness, session_id)
    event = event_payload(
        EventType.CART_VIEWED,
        session_id=session_id,
        sequence_no=1,
        timestamp=datetime.now(timezone.utc),
    )
    assert api_harness.client.post("/api/v1/events", json=event).status_code == 202
    first = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        headers={"Accept-Language": "hi-IN, en;q=0.8"},
        json={"trigger": "CART_VIEWED", "force": True},
    )
    assert first.status_code == 200
    explanation = first.json()["explanation"]
    assert explanation["language"] == "hi"
    assert "निर्णय" in explanation["rendered_text"]

    rejected = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        json={"trigger": "CART_VIEWED", "force": True},
    )
    assert rejected.status_code == 429
