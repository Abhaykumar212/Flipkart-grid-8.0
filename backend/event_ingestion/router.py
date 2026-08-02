from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from backend import config
from backend.deps import get_session_store
from backend.domain.events import EventEnvelope
from backend.storage.db import get_db
from backend.storage.session_store import SessionStore

from .ingest import ingest_events
from .validate import IngestionError

router = APIRouter(prefix="/api/v1/events", tags=["events"])
event_list_adapter = TypeAdapter(list[EventEnvelope])


def _validation_error(error: ValidationError, prefix: tuple[Any, ...]) -> RequestValidationError:
    errors = []
    for item in error.errors():
        errors.append({**item, "loc": (*prefix, *item["loc"])})
    return RequestValidationError(errors)


def _parse_payload(payload: Any) -> list[EventEnvelope]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Request body must be an event or event batch")
    if "events" in payload:
        if set(payload) != {"events"} or not isinstance(payload["events"], list):
            raise HTTPException(status_code=422, detail="Batch body must contain only an events array")
        if len(payload["events"]) > config.MAX_EVENT_BATCH_SIZE:
            raise HTTPException(status_code=413, detail="Event batch exceeds the 50-event limit")
        if not payload["events"]:
            raise HTTPException(status_code=422, detail="Event batch cannot be empty")
        try:
            return event_list_adapter.validate_python(payload["events"])
        except ValidationError as error:
            raise _validation_error(error, ("body", "events")) from error
    try:
        return [EventEnvelope.model_validate(payload)]
    except ValidationError as error:
        raise _validation_error(error, ("body",)) from error


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def post_events(
    payload: Any = Body(...),
    db: Session = Depends(get_db),
    store: SessionStore = Depends(get_session_store),
) -> dict:
    events = _parse_payload(payload)
    try:
        result = ingest_events(events, db, store)
    except IngestionError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    return {
        "accepted": result.accepted,
        "duplicates": result.duplicates,
        "decision_triggered": False,
        "decision_id": None,
        "trace_id": result.trace_id,
    }
