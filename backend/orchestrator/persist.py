from __future__ import annotations

from datetime import datetime
import logging
from time import sleep
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.feature_engine.schema import FEATURE_SCHEMA_VERSION
from backend.explainability.render import render_explanation
from backend.dashboard_api.stream import broadcaster
from backend.feature_engine.snapshot import write_feature_snapshot
from backend.storage.models import DecisionTrace, ModelPrediction, ModelRegistry

from .pipeline import DecisionRun


LOGGER = logging.getLogger(__name__)


def _ensure_model(
    db: Session,
    *,
    name: str,
    version: str,
    model_type: str,
    trained_at: datetime,
) -> None:
    existing = db.scalar(
        select(ModelRegistry).where(
            ModelRegistry.model_name == name,
            ModelRegistry.model_version == version,
        )
    )
    if existing is None:
        db.add(ModelRegistry(
            model_id=f"M-{uuid4().hex}",
            model_name=name,
            model_version=version,
            model_type=model_type,
            artifact_path=f"builtin://{version}",
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            training_data_version="rules-v1",
            trained_at=trained_at,
            metrics={},
            status="SHADOW",
        ))
        db.flush()


def _write(db: Session, run: DecisionRun) -> None:
    if run.risk is None or run.causes is None:
        return
    decision_id = str(run.response["decision_id"])
    recommended = run.response["recommended_intervention"]
    selected = recommended.get("type") if isinstance(recommended, dict) else None
    channel = recommended.get("channel") if isinstance(recommended, dict) else None
    _ensure_model(
        db,
        name="risk-stub",
        version=run.risk.model_version,
        model_type="RISK",
        trained_at=run.decision_time,
    )
    _ensure_model(
        db,
        name="root-cause-stub",
        version=run.causes.model_version,
        model_type="ROOT_CAUSE",
        trained_at=run.decision_time,
    )
    trace = DecisionTrace(
        decision_id=decision_id,
        session_id=run.state.session_id,
        trace_id=run.trace_id,
        decision_time=run.decision_time,
        trigger=run.trigger,
        model_versions={
            "risk": run.risk.model_version,
            "root_cause": run.causes.model_version,
            "ranker": "ranker-rules-v1",
            "policy": "policy-v1",
        },
        abandonment_probability=run.risk.probability,
        risk_band=run.risk.band.value,
        root_causes=[item.to_dict() for item in run.causes.root_causes],
        candidate_interventions=[
            {
                "intervention": item.intervention_id.value,
                "cost_level": item.cost_level.value,
                "intrusiveness": item.intrusiveness,
            }
            for item in run.candidates
        ],
        policy_results=[item.to_dict() for item in run.policy_results],
        utility_scores=[item.to_dict() for item in run.ranked],
        selected_intervention=selected,
        channel=channel,
        recommendation_confidence=float(run.response["confidence_score"]),
        decision=str(run.response["decision"]),
        explanation=run.response["explanation"],
        experiment_id=run.experiment_id,
        experiment_group=run.experiment_group,
        feature_snapshot_id=None,
        latency_ms=run.response["latency_ms"],
    )
    db.add(trace)
    db.flush()
    snapshot = write_feature_snapshot(
        db,
        session_id=run.state.session_id,
        features=run.features,
        computed_at=run.decision_time,
        decision_id=decision_id,
        trigger_event_id=run.trigger_event_id,
    )
    trace.feature_snapshot_id = snapshot.snapshot_id
    for name, model_version, output, latency in (
        ("risk-stub", run.risk.model_version, run.risk.to_dict(), run.risk.latency_ms),
        (
            "root-cause-stub",
            run.causes.model_version,
            run.causes.to_dict(),
            run.causes.latency_ms,
        ),
    ):
        db.add(ModelPrediction(
            prediction_id=f"P-{uuid4().hex}",
            session_id=run.state.session_id,
            decision_id=decision_id,
            model_name=name,
            model_version=model_version,
            predicted_at=run.decision_time,
            output=output,
            latency_ms=latency,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
        ))


def persist_decision(factory: sessionmaker, run: DecisionRun) -> None:
    """Persist the full audit bundle atomically, with one bounded retry."""

    for attempt in range(2):
        try:
            with factory() as db, db.begin():
                _write(db, run)
            recommended = run.response.get("recommended_intervention")
            broadcaster.publish(
                "decision_made",
                {
                    "decision_id": run.response.get("decision_id"),
                    "session_id": run.state.session_id,
                    "decision": run.response.get("decision"),
                    "intervention": (
                        recommended.get("type") if isinstance(recommended, dict) else None
                    ),
                    "probability": run.response.get("abandonment_probability"),
                    "confidence": run.response.get("confidence_score"),
                    "latency_ms": run.response.get("latency_ms"),
                    "trace_id": run.trace_id,
                },
            )
            _render_and_publish(factory, str(run.response["decision_id"]))
            return
        except Exception:
            LOGGER.exception(
                "trace_persist_failed",
                extra={"trace_id": run.trace_id, "attempt": attempt + 1},
            )
            if attempt == 0:
                sleep(0.2)


def _render_and_publish(factory: sessionmaker, decision_id: str) -> None:
    """Render prose off-path, update the trace, then notify dashboard clients."""

    try:
        with factory() as db, db.begin():
            trace = db.get(DecisionTrace, decision_id)
            if trace is None:
                return
            trace.explanation = render_explanation(trace.explanation)
            rendered_by = trace.explanation.get("rendered_by", "template")
        broadcaster.publish(
            "decision_updated",
            {"decision_id": decision_id, "rendered_by": rendered_by},
        )
    except Exception:
        LOGGER.exception("explanation_render_failed", extra={"decision_id": decision_id})
