from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.deps import get_session_store
from backend.storage.db import get_db
from backend.storage.session_store import SessionStore

from .queries import active_sessions, decision_trace, session_detail
from .stream import stream_response


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/sessions")
def get_active_sessions(
    db: Session = Depends(get_db),
    store: SessionStore = Depends(get_session_store),
) -> dict:
    return active_sessions(db, store)


@router.get("/sessions/{session_id}")
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    store: SessionStore = Depends(get_session_store),
) -> dict:
    result = session_detail(session_id, db, store)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.get("/decisions/{decision_id}")
def get_decision_trace(
    decision_id: str,
    db: Session = Depends(get_db),
) -> dict:
    result = decision_trace(decision_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return result


@router.get("/stream")
async def stream_dashboard(request: Request):
    return stream_response(request)
