from datetime import datetime, timezone

from backend.domain.events import EventType
from backend.session_state.rebuild import rebuild_from_events
from backend.session_state.state import SessionState
from tests.event_factories import event_payload

from .test_event_idempotency import _create_session


def test_rebuild_matches_live_state_after_50_events(api_harness):
    client = api_harness.client
    session_id = "rebuild-session"
    _create_session(client, session_id)
    event_cycle = (
        EventType.PRODUCT_VIEWED,
        EventType.REVIEW_OPENED,
        EventType.REVIEW_DWELL_RECORDED,
        EventType.SEARCH_PERFORMED,
        EventType.DELIVERY_CHECKED,
    )
    timestamp = datetime.now(timezone.utc)
    events = [
        event_payload(
            event_cycle[(sequence_no - 1) % len(event_cycle)],
            session_id=session_id,
            sequence_no=sequence_no,
            timestamp=timestamp,
        )
        for sequence_no in range(1, 51)
    ]
    response = client.post("/api/v1/events", json={"events": events})
    assert response.status_code == 202, response.text
    assert response.json()["accepted"] == 50

    live = api_harness.store.get(f"session:{session_id}:state")
    assert isinstance(live, SessionState)
    with api_harness.sessions() as session:
        rebuilt = rebuild_from_events(session_id, session)
    assert rebuilt.to_dict() == live.to_dict()
