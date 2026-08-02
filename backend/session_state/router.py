from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Literal
from sqlalchemy.orm import Session

from backend.deps import get_session_store
from backend.storage.db import get_db
from backend.storage.models import ShoppingSession, User
from backend.storage.session_store import SessionStore

from .cache import cache_session_state
from .rebuild import rebuild_from_events
from .state import SessionState, session_response

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    user_id: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    device_type: Literal["MOBILE", "DESKTOP"] = "DESKTOP"
    referral_source: Annotated[str, Field(min_length=1, max_length=200)] = "DIRECT"
    is_returning_user: bool = False
    is_synthetic: bool = False


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: CreateSessionRequest,
    db: Session = Depends(get_db),
    store: SessionStore = Depends(get_session_store),
) -> dict:
    session_id = payload.session_id or f"S-{uuid4().hex}"
    now = datetime.now(timezone.utc)
    with db.begin():
        if db.get(ShoppingSession, session_id) is not None:
            raise HTTPException(status_code=409, detail="session_id already exists")
        if payload.user_id and db.get(User, payload.user_id) is None:
            raise HTTPException(status_code=404, detail="user_id does not exist")
        db.add(ShoppingSession(
            session_id=session_id,
            user_id=payload.user_id,
            started_at=now,
            device_type=payload.device_type,
            referral_source=payload.referral_source,
            is_returning_user=payload.is_returning_user,
            outcome="OPEN",
            is_synthetic=payload.is_synthetic,
        ))
    state = SessionState(
        session_id=session_id,
        user_id=payload.user_id,
        started_at=now,
        device_type=payload.device_type,
        referral_source=payload.referral_source,
    )
    cache_session_state(store, state)
    return {"session_id": session_id, "experiment_group": None}


@router.get("/{session_id}")
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    store: SessionStore = Depends(get_session_store),
) -> dict:
    state = store.get(f"session:{session_id}:state")
    if not isinstance(state, SessionState):
        try:
            state = rebuild_from_events(session_id, db)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Session not found") from error
        cache_session_state(store, state)
    return session_response(state)
