from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.domain.events import EventType
from backend.storage.models import Event
from tests.event_factories import event_payload

from .test_event_idempotency import _create_session


def test_late_events_persist_and_out_of_order_sequences_are_accepted(api_harness):
    client = api_harness.client
    session_id = "ordering-session"
    _create_session(client, session_id)

    sequence_three = event_payload(
        EventType.PRODUCT_VIEWED,
        session_id=session_id,
        sequence_no=3,
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=10),
    )
    sequence_two = event_payload(
        EventType.REVIEW_OPENED,
        session_id=session_id,
        sequence_no=2,
        timestamp=datetime.now(timezone.utc),
    )
    assert client.post("/api/v1/events", json=sequence_three).status_code == 202
    assert client.post("/api/v1/events", json=sequence_two).status_code == 202

    with api_harness.sessions() as session:
        records = list(session.scalars(
            select(Event).where(Event.session_id == session_id).order_by(Event.server_timestamp)
        ))
    assert [record.sequence_no for record in records] == [3, 2]
    assert records[0].is_late is True
    assert records[1].is_late is False

    reused_sequence = event_payload(
        EventType.PRODUCT_VIEWED,
        session_id=session_id,
        sequence_no=3,
        timestamp=datetime.now(timezone.utc),
    )
    conflict = client.post("/api/v1/events", json=reused_sequence)
    assert conflict.status_code == 409
