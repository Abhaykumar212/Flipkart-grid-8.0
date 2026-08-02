from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from time import perf_counter
from uuid import uuid4

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from backend import config
from backend.dashboard_api.stream import broadcaster
from backend.domain.events import EventEnvelope, EventType
from backend.observability.logging import log_event
from backend.session_state.cache import cache_session_state
from backend.session_state.rebuild import rebuild_from_events
from backend.session_state.state import SessionState
from backend.session_state.updater import apply
from backend.storage.models import Event, ShoppingSession
from backend.storage.session_store import SessionStore

from .validate import validate_references_and_transition

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    accepted: int
    duplicates: int
    trace_id: str
    latency_ms: float


def _insert_event(db: Session, values: dict) -> bool:
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        statement = sqlite_insert(Event).values(**values).on_conflict_do_nothing(
            index_elements=[Event.event_id]
        )
    elif dialect == "postgresql":
        statement = postgresql_insert(Event).values(**values).on_conflict_do_nothing(
            index_elements=[Event.event_id]
        )
    else:
        if db.get(Event, values["event_id"]) is not None:
            return False
        db.add(Event(**values))
        db.flush()
        return True
    result = db.execute(statement)
    return result.rowcount == 1


def _new_session(event: EventEnvelope) -> ShoppingSession:
    metadata = event.metadata.model_dump()
    return ShoppingSession(
        session_id=event.session_id,
        user_id=event.user_id,
        started_at=event.client_timestamp,
        device_type=metadata["device_type"],
        referral_source=metadata["referral_source"],
        is_returning_user=False,
        outcome="OPEN",
        is_synthetic=False,
    )


def ingest_events(
    events: list[EventEnvelope],
    db: Session,
    store: SessionStore,
) -> IngestionResult:
    started = perf_counter()
    trace_id = f"tr_{uuid4().hex}"
    accepted = 0
    duplicates = 0
    states: dict[str, SessionState] = {}
    accepted_event_ids: dict[str, list[str]] = {}

    with db.begin():
        for envelope in events:
            event_id = str(envelope.event_id)
            if db.get(Event, event_id) is not None:
                duplicates += 1
                continue

            state = states.get(envelope.session_id)
            if state is None:
                cached = store.get(f"session:{envelope.session_id}:state")
                if isinstance(cached, SessionState):
                    state = cached
                elif db.get(ShoppingSession, envelope.session_id) is not None:
                    state = rebuild_from_events(envelope.session_id, db)

            shopping_session = validate_references_and_transition(
                db,
                envelope,
                state,
                trace_id=trace_id,
            )
            if envelope.event_type == EventType.SESSION_STARTED:
                if shopping_session is None:
                    shopping_session = _new_session(envelope)
                    db.add(shopping_session)
                    db.flush()
                else:
                    metadata = envelope.metadata.model_dump()
                    shopping_session.started_at = envelope.client_timestamp
                    shopping_session.user_id = envelope.user_id
                    shopping_session.device_type = metadata["device_type"]
                    shopping_session.referral_source = metadata["referral_source"]
                if state is None:
                    state = SessionState(
                        session_id=envelope.session_id,
                        user_id=envelope.user_id,
                        started_at=envelope.client_timestamp,
                    )

            if state is None:
                state = rebuild_from_events(envelope.session_id, db)

            server_timestamp = datetime.now(timezone.utc)
            is_late = (
                server_timestamp - envelope.client_timestamp.astimezone(timezone.utc)
            ).total_seconds() > config.EVENT_LATE_THRESHOLD_SECONDS
            inserted = _insert_event(db, {
                "event_id": event_id,
                "session_id": envelope.session_id,
                "user_id": envelope.user_id,
                "event_type": envelope.event_type.value,
                "product_id": envelope.product_id,
                "sequence_no": envelope.sequence_no,
                "client_timestamp": envelope.client_timestamp,
                "server_timestamp": server_timestamp,
                "metadata_json": envelope.metadata.model_dump(mode="json"),
                "is_late": is_late,
            })
            if not inserted:
                duplicates += 1
                continue

            accepted += 1
            accepted_event_ids.setdefault(envelope.session_id, []).append(event_id)
            state = apply(
                state,
                envelope,
                server_timestamp=server_timestamp,
                is_late=is_late,
            )
            states[envelope.session_id] = state
            if envelope.event_type == EventType.ORDER_COMPLETED:
                shopping_session.outcome = "CONVERTED"
                shopping_session.outcome_resolved_at = server_timestamp
            elif envelope.event_type == EventType.SESSION_ENDED:
                shopping_session.ended_at = server_timestamp
                if shopping_session.outcome == "OPEN":
                    shopping_session.outcome = "ABANDONED"
                    shopping_session.outcome_resolved_at = server_timestamp

    for session_id, state in states.items():
        cache_session_state(
            store,
            state,
            event_ids=accepted_event_ids.get(session_id, ()),
        )

    latency_ms = round((perf_counter() - started) * 1000, 3)
    log_event(
        LOGGER,
        "events_ingested",
        trace_id=trace_id,
        session_id=events[0].session_id if len({event.session_id for event in events}) == 1 else None,
        accepted=accepted,
        duplicates=duplicates,
        latency_ms=latency_ms,
    )
    broadcaster.publish(
        "event_ingested",
        {
            "trace_id": trace_id,
            "session_id": (
                events[0].session_id
                if len({event.session_id for event in events}) == 1
                else None
            ),
            "session_ids": sorted({event.session_id for event in events}),
            "event_types": [event.event_type.value for event in events],
            "accepted": accepted,
            "duplicates": duplicates,
            "latency_ms": latency_ms,
        },
    )
    return IngestionResult(accepted, duplicates, trace_id, latency_ms)
