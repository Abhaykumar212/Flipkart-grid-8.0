from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend import config
from backend.deps import get_session_store
from backend.domain.interventions import InterventionId
from backend.explainability.templates import INTERVENTION_COPY, action_statement
from backend.recommendation.catalogue import CATALOGUE_BY_ID
from backend.session_state.cache import cache_session_state
from backend.session_state.rebuild import rebuild_from_events
from backend.session_state.state import SessionState
from backend.storage.db import get_db
from backend.storage.models import DecisionTrace, ShoppingSession
from backend.storage.session_store import SessionStore
from backend.observability.rate_limit import decision_rate_limiter
from backend.explainability.i18n import resolve_language

from .persist import persist_decision
from .pipeline import run_decision
from .triggers import TRIGGER_NAMES


router = APIRouter(prefix="/api/v1/sessions", tags=["decisions"])


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger: str
    force: bool = False


@router.post("/{session_id}/decisions")
def decide(
    session_id: str,
    payload: DecisionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    store: SessionStore = Depends(get_session_store),
    accept_language: str | None = Header(default=None),
) -> dict[str, object]:
    if db.get(ShoppingSession, session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.trigger not in TRIGGER_NAMES:
        raise HTTPException(status_code=422, detail="Unsupported decision trigger")
    rate_limit = decision_rate_limiter.acquire(
        session_id,
        limit=config.DECISION_RATE_LIMIT_PER_MINUTE,
    )
    if not rate_limit.allowed:
        raise HTTPException(
            status_code=429,
            detail="Decision rate limit exceeded",
            headers={"Retry-After": str(rate_limit.retry_after_seconds)},
        )
    run = run_decision(
        session_id,
        payload.trigger,
        db,
        store,
        force=payload.force,
        language=resolve_language(accept_language),
    )
    if run.experiment_id is not None:
        db.commit()
    if run.should_persist:
        factory = sessionmaker(
            bind=db.get_bind(), autoflush=False, expire_on_commit=False
        )
        background_tasks.add_task(persist_decision, factory, run)
    return run.response


@router.get("/{session_id}/interventions/latest", response_model=None)
def latest_intervention(
    session_id: str,
    db: Session = Depends(get_db),
    store: SessionStore = Depends(get_session_store),
) -> dict[str, object] | Response:
    if db.get(ShoppingSession, session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    state = store.get(f"session:{session_id}:state")
    if not isinstance(state, SessionState):
        state = rebuild_from_events(session_id, db)
        cache_session_state(store, state)
    response = state.last_decision.get("response", {}) if state.last_decision else {}
    recommended = response.get("recommended_intervention")
    decision_id = response.get("decision_id")
    explanation = response.get("explanation")
    if response.get("decision") != "INTERVENE" or not isinstance(recommended, dict):
        trace = db.scalar(
            select(DecisionTrace)
            .where(DecisionTrace.session_id == session_id)
            .order_by(DecisionTrace.decision_time.desc())
            .limit(1)
        )
        if (
            trace is None
            or trace.decision != "INTERVENE"
            or not trace.selected_intervention
            or trace.selected_intervention == InterventionId.NO_ACTION.value
        ):
            return Response(status_code=204)
        intervention_id = InterventionId(trace.selected_intervention)
        definition = CATALOGUE_BY_ID[intervention_id]
        headline, body, cta_label = INTERVENTION_COPY[intervention_id]
        decision_id = trace.decision_id
        recommended = {
            "decision_id": decision_id,
            "type": intervention_id.value,
            "display_name": definition.display_name,
            "channel": trace.channel,
            "headline": headline,
            "body": body,
            "cta_label": cta_label,
            "reason": action_statement(intervention_id),
            "confidence": trace.recommendation_confidence,
        }
        if intervention_id == InterventionId.REVIEW_SUMMARY:
            product_ids = [
                str(item.get("product_id"))
                for item in state.cart.get("items", [])
                if isinstance(item, dict) and item.get("product_id")
            ]
            recommended["review_product_id"] = (
                product_ids[0] if product_ids else state.current_product_id
            )
        if intervention_id == InterventionId.LIMITED_TIME_DISCOUNT:
            recommended["discount_pct"] = min(
                config.DEFAULT_DISCOUNT_PCT,
                definition.max_discount_pct or config.DEFAULT_DISCOUNT_PCT,
            )
        explanation = trace.explanation
    if any(
        shown.get("decision_id") == decision_id and shown.get("outcome") == "DISMISSED"
        for shown in state.interventions.get("shown", [])
    ):
        return Response(status_code=204)
    return {
        "decision_id": decision_id,
        "recommended_intervention": recommended,
        "explanation": explanation,
    }
