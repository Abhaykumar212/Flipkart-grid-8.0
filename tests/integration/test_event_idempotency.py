from datetime import datetime, timezone
from time import perf_counter

from sqlalchemy import func, select

from backend.domain.events import EventType
from backend.storage.models import Event
from tests.event_factories import event_payload


def _create_session(client, session_id: str) -> None:
    response = client.post("/api/v1/sessions", json={"session_id": session_id})
    assert response.status_code == 201, response.text


def test_duplicate_event_is_acknowledged_once(api_harness):
    client = api_harness.client
    _create_session(client, "idempotent-session")
    payload = event_payload(
        EventType.PRODUCT_VIEWED,
        session_id="idempotent-session",
        sequence_no=1,
        timestamp=datetime.now(timezone.utc),
    )

    first = client.post("/api/v1/events", json=payload)
    second = client.post("/api/v1/events", json=payload)

    assert first.status_code == 202
    assert first.json()["accepted"] == 1
    assert second.status_code == 202
    assert second.json()["duplicates"] == 1
    with api_harness.sessions() as session:
        count = session.scalar(
            select(func.count()).select_from(Event).where(Event.session_id == "idempotent-session")
        )
    assert count == 1
    state = client.get("/api/v1/sessions/idempotent-session").json()
    assert state["counters"]["product_views"] == 1
    assert api_harness.store.get("session:idempotent-session:events")
    assert api_harness.store.get("session:idempotent-session:counters")["product_views"] == 1
    assert api_harness.store.get(f"dedupe:event:{payload['event_id']}") == 1


def test_ingestion_p95_is_below_budget(api_harness):
    client = api_harness.client
    _create_session(client, "latency-session")
    latencies = []
    for sequence_no in range(1, 101):
        payload = event_payload(
            EventType.PRODUCT_VIEWED,
            session_id="latency-session",
            sequence_no=sequence_no,
            timestamp=datetime.now(timezone.utc),
        )
        started = perf_counter()
        response = client.post("/api/v1/events", json=payload)
        latencies.append((perf_counter() - started) * 1000)
        assert response.status_code == 202

    p95 = sorted(latencies)[94]
    assert p95 < 100, f"event ingestion p95 was {p95:.2f} ms"
