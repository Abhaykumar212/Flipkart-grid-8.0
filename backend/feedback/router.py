from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.storage.db import get_db

from .outcomes import record_impression, record_outcome


router = APIRouter(prefix="/api/v1/decisions", tags=["feedback"])


class ImpressionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surface: str = "unknown"


class OutcomeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clicked: bool = False
    dismissed: bool = False
    order_completed: bool = False


@router.post("/{decision_id}/impression")
def impression(
    decision_id: str,
    payload: ImpressionRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        with db.begin():
            return record_impression(db, decision_id, surface=payload.surface)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Decision not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{decision_id}/outcome")
def outcome(
    decision_id: str,
    payload: OutcomeRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        with db.begin():
            return record_outcome(
                db,
                decision_id,
                clicked=payload.clicked,
                dismissed=payload.dismissed,
                order_completed=payload.order_completed,
            )
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Decision not found") from error
