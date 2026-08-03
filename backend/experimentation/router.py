from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.storage.db import get_db

from .metrics import experiment_metrics


router = APIRouter(prefix="/api/v1/dashboard/experiments", tags=["experiments"])


@router.get("/{experiment_id}/metrics")
def metrics(experiment_id: str, db: Session = Depends(get_db)) -> dict:
    result = experiment_metrics(db, experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return result
