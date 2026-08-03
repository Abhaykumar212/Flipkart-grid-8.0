from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.deps import get_session_store
from backend.storage.db import get_db
from backend.storage.session_store import SessionStore

from .fixtures import scenario_catalogue
from .replay import replay_scenario
from .simulate import simulate_traffic


router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessions: int = Field(default=24, ge=1, le=120)
    seed: int | None = None


@router.get("/scenarios")
def list_scenarios() -> dict:
    """Describe the frozen proof scenarios without running them."""

    catalogue = scenario_catalogue()
    return {"scenarios": catalogue, "count": len(catalogue)}


@router.post("/scenarios/{letter}/run")
def run_scenario(
    letter: str,
    db: Session = Depends(get_db),
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """Replay one scenario through the real decision path."""

    try:
        return replay_scenario(letter, db, store)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Unknown scenario") from error


@router.post("/simulate")
def simulate(
    payload: SimulateRequest | None = None,
    db: Session = Depends(get_db),
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """Generate synthetic traffic so experiment and drift panels have data."""

    request = payload or SimulateRequest()
    return simulate_traffic(db, store, sessions=request.sessions, seed=request.seed)
