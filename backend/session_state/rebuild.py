from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.events import EventEnvelope
from backend.storage.models import Event, ShoppingSession

from .state import SessionState
from .updater import apply


def rebuild_from_events(session_id: str, db: Session) -> SessionState:
    shopping_session = db.get(ShoppingSession, session_id)
    if shopping_session is None:
        raise KeyError(session_id)

    started_at = shopping_session.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    state = SessionState(
        session_id=session_id,
        user_id=shopping_session.user_id,
        started_at=started_at,
        device_type=shopping_session.device_type,
        referral_source=shopping_session.referral_source,
        is_returning_user=shopping_session.is_returning_user,
        ended=shopping_session.ended_at is not None,
        order_completed=shopping_session.outcome == "CONVERTED",
    )
    records = db.scalars(
        select(Event)
        .where(Event.session_id == session_id)
        .order_by(Event.server_timestamp, Event.sequence_no)
    )
    for record in records:
        client_timestamp = record.client_timestamp
        server_timestamp = record.server_timestamp
        if client_timestamp.tzinfo is None:
            client_timestamp = client_timestamp.replace(tzinfo=timezone.utc)
        if server_timestamp.tzinfo is None:
            server_timestamp = server_timestamp.replace(tzinfo=timezone.utc)
        envelope = EventEnvelope.model_validate({
            "event_id": record.event_id,
            "event_type": record.event_type,
            "session_id": record.session_id,
            "user_id": record.user_id,
            "product_id": record.product_id,
            "sequence_no": record.sequence_no,
            "client_timestamp": client_timestamp,
            "metadata": record.metadata_json,
        })
        state = apply(
            state,
            envelope,
            server_timestamp=server_timestamp,
            is_late=record.is_late,
        )
    return state
