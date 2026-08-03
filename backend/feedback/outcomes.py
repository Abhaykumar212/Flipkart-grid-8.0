from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import config
from backend.dashboard_api.stream import broadcaster
from backend.domain.enums import CostLevel
from backend.domain.interventions import InterventionId
from backend.recommendation.catalogue import CATALOGUE_BY_ID
from backend.storage.models import (
    DecisionTrace,
    InterventionImpression,
    InterventionOutcome,
    ShoppingSession,
)
from backend.recommendation.bandit import live_bandit, reward_value


FIXED_INTERVENTION_COST = {
    CostLevel.ZERO.value: 0.0,
    CostLevel.LOW.value: 2.0,
    CostLevel.MEDIUM.value: 8.0,
    CostLevel.HIGH.value: 25.0,
}


def _utc(value: datetime | None = None) -> datetime:
    value = value or datetime.now(timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _outcome_for_update(db: Session, decision_id: str, now: datetime) -> InterventionOutcome:
    outcome = db.scalar(
        select(InterventionOutcome).where(InterventionOutcome.decision_id == decision_id)
    )
    if outcome is None:
        outcome = InterventionOutcome(
            outcome_id=f"O-{uuid4().hex}",
            decision_id=decision_id,
            intervention_shown=False,
            clicked=False,
            dismissed=False,
            order_completed=False,
            discount_cost=0.0,
            estimated_margin=None,
            recorded_at=now,
        )
        db.add(outcome)
        db.flush()
    return outcome


def _row(outcome: InterventionOutcome) -> dict[str, object]:
    return {
        "outcome_id": outcome.outcome_id,
        "decision_id": outcome.decision_id,
        "intervention_shown": outcome.intervention_shown,
        "clicked": outcome.clicked,
        "dismissed": outcome.dismissed,
        "order_completed": outcome.order_completed,
        "time_to_purchase_seconds": outcome.time_to_purchase_seconds,
        "discount_cost": outcome.discount_cost,
        "estimated_margin": outcome.estimated_margin,
        "recorded_at": _utc(outcome.recorded_at).isoformat(),
    }


def record_impression(
    db: Session,
    decision_id: str,
    *,
    surface: str,
    shown_at: datetime | None = None,
) -> dict[str, object]:
    now = _utc(shown_at)
    trace = db.get(DecisionTrace, decision_id)
    if trace is None:
        raise KeyError(decision_id)
    if not trace.selected_intervention:
        raise ValueError("decision has no selected intervention")
    impression = db.scalar(
        select(InterventionImpression).where(
            InterventionImpression.decision_id == decision_id
        )
    )
    if impression is None:
        impression = InterventionImpression(
            impression_id=f"I-{uuid4().hex}",
            decision_id=decision_id,
            session_id=trace.session_id,
            intervention_id=trace.selected_intervention,
            channel=trace.channel or "UNKNOWN",
            shown_at=now,
            surface=surface,
        )
        db.add(impression)
    outcome = _outcome_for_update(db, decision_id, now)
    outcome.intervention_shown = True
    outcome.recorded_at = now
    db.flush()
    payload = {
        "decision_id": decision_id,
        "session_id": trace.session_id,
        "intervention_id": trace.selected_intervention,
        "surface": surface,
    }
    broadcaster.publish("intervention_shown", payload)
    return payload


def record_outcome(
    db: Session,
    decision_id: str,
    *,
    clicked: bool = False,
    dismissed: bool = False,
    order_completed: bool = False,
    now: datetime | None = None,
) -> dict[str, object]:
    recorded_at = _utc(now)
    trace = db.get(DecisionTrace, decision_id)
    if trace is None:
        raise KeyError(decision_id)
    outcome = _outcome_for_update(db, decision_id, recorded_at)
    outcome.clicked = outcome.clicked or clicked
    outcome.dismissed = outcome.dismissed or dismissed
    outcome.order_completed = outcome.order_completed or order_completed
    outcome.recorded_at = recorded_at
    db.flush()
    payload = _row(outcome)
    broadcaster.publish(
        "outcome_recorded",
        {"decision_id": decision_id, "session_id": trace.session_id, **payload},
    )
    return payload


def _discount_pct(trace: DecisionTrace) -> float:
    if trace.selected_intervention != InterventionId.LIMITED_TIME_DISCOUNT.value:
        return 0.0
    definition = CATALOGUE_BY_ID[InterventionId.LIMITED_TIME_DISCOUNT]
    return min(config.DEFAULT_DISCOUNT_PCT, definition.max_discount_pct or config.DEFAULT_DISCOUNT_PCT) / 100.0


def _fixed_cost(trace: DecisionTrace) -> float:
    if not trace.selected_intervention:
        return 0.0
    try:
        definition = CATALOGUE_BY_ID[InterventionId(trace.selected_intervention)]
        return FIXED_INTERVENTION_COST[definition.cost_level.value]
    except (KeyError, ValueError):
        return 0.0


def resolve_session(
    db: Session,
    session_id: str,
    *,
    converted: bool,
    order_value: float = 0.0,
    resolved_at: datetime | None = None,
) -> list[dict[str, object]]:
    now = _utc(resolved_at)
    session = db.get(ShoppingSession, session_id)
    if session is not None:
        session.outcome = "CONVERTED" if converted else "ABANDONED"
        session.outcome_resolved_at = now
        if not converted and session.ended_at is None:
            session.ended_at = now

    traces = list(db.scalars(
        select(DecisionTrace)
        .where(DecisionTrace.session_id == session_id)
        .order_by(DecisionTrace.decision_time)
    ))
    resolved: list[dict[str, object]] = []
    for trace in traces:
        outcome = _outcome_for_update(db, trace.decision_id, now)
        if outcome.order_completed:
            resolved.append(_row(outcome))
            continue
        outcome.order_completed = converted
        outcome.time_to_purchase_seconds = (
            max(0.0, (now - _utc(trace.decision_time)).total_seconds())
            if converted else None
        )
        if converted:
            discount_cost = order_value * _discount_pct(trace)
            outcome.discount_cost = round(discount_cost, 2)
            outcome.estimated_margin = round(
                order_value * 0.18 - discount_cost - _fixed_cost(trace),
                2,
            )
        else:
            outcome.discount_cost = 0.0
            outcome.estimated_margin = 0.0
        outcome.recorded_at = now
        dominant_cause = max(
            trace.root_causes,
            key=lambda item: float(item.get("probability", 0.0)),
            default={"cause": "UNKNOWN"},
        ).get("cause", "UNKNOWN")
        if trace.selected_intervention:
            raw_reward = reward_value(
                conversion_value=(order_value * 0.18 if converted else 0.0),
                intervention_cost=_fixed_cost(trace),
                discount_cost=outcome.discount_cost,
                dismissed=outcome.dismissed,
            )
            # Beta posteriors accept [0,1]. A profitable conversion is a success;
            # zero/negative margin, dismissal, or abandonment is a failure.
            live_bandit.observe(
                trace.selected_intervention,
                str(dominant_cause),
                float(raw_reward > 0),
            )
        resolved.append(_row(outcome))
    db.flush()
    broadcaster.publish(
        "outcome_recorded",
        {"session_id": session_id, "converted": converted, "resolved": len(resolved)},
    )
    return resolved
