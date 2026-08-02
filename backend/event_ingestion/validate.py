import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.events import EventEnvelope, EventType
from backend.observability.logging import log_event
from backend.session_state.state import SessionState
from backend.storage.models import DecisionTrace, Event, Product, ShoppingSession, User


LOGGER = logging.getLogger(__name__)


class IngestionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def validate_references_and_transition(
    db: Session,
    event: EventEnvelope,
    state: SessionState | None,
    *,
    trace_id: str,
) -> ShoppingSession | None:
    shopping_session = db.get(ShoppingSession, event.session_id)

    if event.event_type == EventType.SESSION_STARTED:
        existing_start = db.scalar(
            select(Event.event_id).where(
                Event.session_id == event.session_id,
                Event.event_type == EventType.SESSION_STARTED.value,
            ).limit(1)
        )
        if existing_start:
            raise IngestionError(409, "SESSION_STARTED has already been recorded")
    elif shopping_session is None:
        raise IngestionError(404, f"Unknown session_id: {event.session_id}")

    if event.user_id and db.get(User, event.user_id) is None:
        raise IngestionError(404, f"Unknown user_id: {event.user_id}")

    if event.product_id and db.get(Product, event.product_id) is None:
        raise IngestionError(404, f"Unknown product_id: {event.product_id}")

    sequence_owner = db.scalar(
        select(Event.event_id).where(
            Event.session_id == event.session_id,
            Event.sequence_no == event.sequence_no,
        ).limit(1)
    )
    if sequence_owner and sequence_owner != str(event.event_id):
        raise IngestionError(409, f"sequence_no {event.sequence_no} is already in use")

    if state and state.ended:
        raise IngestionError(409, "Events cannot be added after SESSION_ENDED")
    if state and state.order_completed and event.event_type == EventType.ITEM_ADDED_TO_CART:
        raise IngestionError(409, "ITEM_ADDED_TO_CART is invalid after ORDER_COMPLETED")

    if (
        event.event_type == EventType.CHECKOUT_STEP_VIEWED
        and state
        and state.counters["checkout_starts"] == 0
    ):
        log_event(
            LOGGER,
            "checkout_step_without_start",
            trace_id=trace_id,
            session_id=event.session_id,
            sequence_no=event.sequence_no,
        )

    if event.event_type in {EventType.INTERVENTION_CLICKED, EventType.INTERVENTION_DISMISSED}:
        decision_id = event.metadata.decision_id
        decision = db.get(DecisionTrace, decision_id)
        if decision is None or decision.session_id != event.session_id:
            raise IngestionError(404, f"Unknown decision_id: {decision_id}")
        if decision.selected_intervention != event.metadata.intervention_id:
            raise IngestionError(409, "intervention_id does not match the decision")

    return shopping_session
