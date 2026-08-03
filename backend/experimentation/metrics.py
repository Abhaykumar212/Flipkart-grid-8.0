from __future__ import annotations

from math import sqrt
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.storage.models import (
    DecisionTrace,
    Experiment,
    ExperimentAssignment,
    InterventionImpression,
    InterventionOutcome,
    Order,
)


def _rate(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _arm_metrics(db: Session, experiment_id: str, group_name: str) -> dict[str, Any]:
    sessions = int(db.scalar(
        select(func.count()).select_from(ExperimentAssignment).where(
            ExperimentAssignment.experiment_id == experiment_id,
            ExperimentAssignment.group_name == group_name,
        )
    ) or 0)
    traces = list(db.scalars(
        select(DecisionTrace).where(
            DecisionTrace.experiment_id == experiment_id,
            DecisionTrace.experiment_group == group_name,
        )
    ))
    decision_ids = [trace.decision_id for trace in traces]
    outcomes = list(db.scalars(
        select(InterventionOutcome).where(InterventionOutcome.decision_id.in_(decision_ids))
    )) if decision_ids else []
    impressions = int(db.scalar(
        select(func.count()).select_from(InterventionImpression).where(
            InterventionImpression.decision_id.in_(decision_ids)
        )
    ) or 0) if decision_ids else 0
    conversions = sum(1 for outcome in outcomes if outcome.order_completed)
    clicks = sum(1 for outcome in outcomes if outcome.clicked)
    dismissals = sum(1 for outcome in outcomes if outcome.dismissed)
    purchase_times = [
        float(outcome.time_to_purchase_seconds)
        for outcome in outcomes
        if outcome.time_to_purchase_seconds is not None
    ]
    session_ids = [assignment.session_id for assignment in db.scalars(
        select(ExperimentAssignment).where(
            ExperimentAssignment.experiment_id == experiment_id,
            ExperimentAssignment.group_name == group_name,
        )
    )]
    revenue = float(db.scalar(
        select(func.coalesce(func.sum(Order.order_value), 0.0)).where(
            Order.session_id.in_(session_ids)
        )
    ) or 0.0) if session_ids else 0.0
    # Live order revenue is represented through converted outcome margin in the
    # current schema; total revenue is added by Phase 16 scenario orders.
    total_discount = sum(float(outcome.discount_cost) for outcome in outcomes)
    total_margin = sum(float(outcome.estimated_margin or 0.0) for outcome in outcomes)
    return {
        "group": group_name,
        "sessions": sessions,
        "decisions": len(traces),
        "interventions_shown": impressions,
        "intervention_rate": _rate(impressions, sessions),
        "ctr": _rate(clicks, impressions),
        "dismissal_rate": _rate(dismissals, impressions),
        "conversion_rate": _rate(conversions, sessions),
        "mean_time_to_purchase_seconds": (
            sum(purchase_times) / len(purchase_times) if purchase_times else None
        ),
        "total_discount_cost": round(total_discount, 2),
        "total_revenue": round(revenue, 2),
        "estimated_margin": round(total_margin, 2),
        "margin_per_session": _rate(total_margin, sessions),
        "interventions_per_session": _rate(impressions, sessions),
    }


def experiment_metrics(db: Session, experiment_id: str) -> dict[str, Any] | None:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        return None
    control = _arm_metrics(db, experiment_id, experiment.control_group)
    treatment = _arm_metrics(db, experiment_id, experiment.treatment_group)
    p_c = control["conversion_rate"]
    p_t = treatment["conversion_rate"]
    n_c = control["sessions"]
    n_t = treatment["sessions"]
    absolute = p_t - p_c
    ci = (
        1.96 * sqrt((p_t * (1 - p_t) / n_t) + (p_c * (1 - p_c) / n_c))
        if n_t and n_c else None
    )
    significant = bool(ci is not None and abs(absolute) > ci)
    return {
        "experiment": {
            "experiment_id": experiment.experiment_id,
            "name": experiment.name,
            "status": experiment.status,
            "traffic_split": experiment.traffic_split,
            "control_group": experiment.control_group,
            "treatment_group": experiment.treatment_group,
        },
        "arms": {control["group"]: control, treatment["group"]: treatment},
        "uplift": {
            "absolute": absolute,
            "relative": (absolute / p_c if p_c else None),
            "ci95": ci,
            "label": "significant" if significant else "inconclusive",
        },
    }
