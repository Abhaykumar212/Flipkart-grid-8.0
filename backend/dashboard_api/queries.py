from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.feature_engine.compute import compute_features
from backend.feature_engine.schema import FEATURE_SCHEMA_VERSION
from backend.session_state.rebuild import rebuild_from_events
from backend.session_state.state import SessionState
from backend.storage.models import (
    DecisionTrace,
    Event,
    InterventionImpression,
    InterventionOutcome,
    InterventionCatalogue,
    ModelRegistry,
    Product,
    SessionFeatureSnapshot,
    ShoppingSession,
)
from backend.storage.repositories import user_history
from backend.storage.session_store import SessionStore


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _state(session_id: str, db: Session, store: SessionStore) -> SessionState:
    cached = store.get(f"session:{session_id}:state")
    return cached if isinstance(cached, SessionState) else rebuild_from_events(session_id, db)


def _decision_summary(trace: DecisionTrace) -> dict[str, Any]:
    return {
        "decision_id": trace.decision_id,
        "decision_time": _iso(trace.decision_time),
        "decision": trace.decision,
        "probability": trace.abandonment_probability,
        "risk_band": trace.risk_band,
        "selected_intervention": trace.selected_intervention,
        "confidence": trace.recommendation_confidence,
        "trigger": trace.trigger,
    }


def _outcome_summary(db: Session, decision_id: str) -> dict[str, Any] | None:
    outcome = db.scalar(
        select(InterventionOutcome).where(InterventionOutcome.decision_id == decision_id)
    )
    if outcome is None:
        return None
    impression = db.scalar(
        select(InterventionImpression).where(InterventionImpression.decision_id == decision_id)
    )
    return {
        "intervention_shown": outcome.intervention_shown,
        "clicked": outcome.clicked,
        "dismissed": outcome.dismissed,
        "order_completed": outcome.order_completed,
        "time_to_purchase_seconds": outcome.time_to_purchase_seconds,
        "discount_cost": outcome.discount_cost,
        "estimated_margin": outcome.estimated_margin,
        "recorded_at": _iso(outcome.recorded_at),
        "impression": ({
            "shown_at": _iso(impression.shown_at),
            "surface": impression.surface,
            "channel": impression.channel,
        } if impression else None),
    }


def active_sessions(db: Session, store: SessionStore) -> dict[str, Any]:
    sessions = list(db.scalars(
        select(ShoppingSession)
        .where(ShoppingSession.ended_at.is_(None), ShoppingSession.outcome == "OPEN")
        .order_by(ShoppingSession.started_at.desc())
    ))
    rows: list[dict[str, Any]] = []
    for session in sessions:
        state = _state(session.session_id, db, store)
        latest = db.scalar(
            select(DecisionTrace)
            .where(DecisionTrace.session_id == session.session_id)
            .order_by(DecisionTrace.decision_time.desc())
            .limit(1)
        )
        rows.append({
            "session_id": session.session_id,
            "user_id": session.user_id,
            "started_at": _iso(session.started_at),
            "last_event_at": _iso(state.last_event_at),
            "device_type": session.device_type,
            "referral_source": session.referral_source,
            "current_route": state.current_route,
            "cart_value": float(state.cart.get("value", 0.0)),
            "item_count": int(state.cart.get("item_count", 0)),
            "event_count": max(
                (int(item.get("sequence_no", 0)) for item in state.recent_events),
                default=0,
            ),
            "latest_decision": _decision_summary(latest) if latest else None,
        })
    return {
        "sessions": rows,
        "count": len(rows),
        "generated_at": _iso(datetime.now(timezone.utc)),
    }


def session_detail(session_id: str, db: Session, store: SessionStore) -> dict[str, Any] | None:
    session = db.get(ShoppingSession, session_id)
    if session is None:
        return None
    state = _state(session_id, db, store)
    events = list(db.scalars(
        select(Event)
        .where(Event.session_id == session_id)
        .order_by(Event.server_timestamp, Event.sequence_no)
    ))
    decisions = list(db.scalars(
        select(DecisionTrace)
        .where(DecisionTrace.session_id == session_id)
        .order_by(DecisionTrace.decision_time.desc())
    ))
    snapshot = db.scalar(
        select(SessionFeatureSnapshot)
        .where(SessionFeatureSnapshot.session_id == session_id)
        .order_by(SessionFeatureSnapshot.computed_at.desc())
        .limit(1)
    )
    if snapshot is None:
        computed_at = datetime.now(timezone.utc)
        feature_snapshot = {
            "snapshot_id": None,
            "computed_at": _iso(computed_at),
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "features": compute_features(
                state, user_history(db, state.user_id, as_of=computed_at)
            ),
            "source": "LIVE",
        }
    else:
        feature_snapshot = {
            "snapshot_id": snapshot.snapshot_id,
            "computed_at": _iso(snapshot.computed_at),
            "feature_schema_version": snapshot.feature_schema_version,
            "features": snapshot.features,
            "source": "PERSISTED",
        }

    product_ids = {str(item.get("product_id")) for item in state.cart.get("items", [])}
    products = {
        product.product_id: product
        for product in db.scalars(select(Product).where(Product.product_id.in_(product_ids)))
    } if product_ids else {}
    cart = dict(state.cart)
    cart["items"] = [
        {
            **item,
            "title": products[str(item.get("product_id"))].title
            if str(item.get("product_id")) in products else None,
            "brand": products[str(item.get("product_id"))].brand
            if str(item.get("product_id")) in products else None,
        }
        for item in state.cart.get("items", [])
    ]
    return {
        "session": {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "started_at": _iso(session.started_at),
            "ended_at": _iso(session.ended_at),
            "last_event_at": _iso(state.last_event_at),
            "device_type": session.device_type,
            "referral_source": session.referral_source,
            "current_route": state.current_route,
            "outcome": session.outcome,
        },
        "timeline": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "sequence_no": event.sequence_no,
                "product_id": event.product_id,
                "client_timestamp": _iso(event.client_timestamp),
                "server_timestamp": _iso(event.server_timestamp),
                "metadata": event.metadata_json,
                "is_late": event.is_late,
            }
            for event in events
        ],
        "cart": cart,
        "counters": state.counters,
        "feature_snapshot": feature_snapshot,
        "decisions": [_decision_summary(trace) for trace in decisions],
        "outcomes": {
            trace.decision_id: _outcome_summary(db, trace.decision_id)
            for trace in decisions
        },
        "interventions": state.interventions,
    }


def _candidate_rows(trace: DecisionTrace, db: Session) -> list[dict[str, Any]]:
    generated = {
        str(item["intervention"]): item for item in trace.candidate_interventions
    }
    policy = {str(item["intervention"]): item for item in trace.policy_results}
    utility = {str(item["intervention"]): item for item in trace.utility_scores}
    rejected = {
        str(item["intervention"]): item
        for item in trace.explanation.get("rejected", [])
    }
    ordered_ids = list(generated)
    for source in (policy, utility, rejected):
        ordered_ids.extend(item for item in source if item not in ordered_ids)
    catalogue = {
        item.intervention_id: item
        for item in db.scalars(
            select(InterventionCatalogue).where(
                InterventionCatalogue.intervention_id.in_(ordered_ids)
            )
        )
    } if ordered_ids else {}
    rows = []
    for intervention_id in ordered_ids:
        definition = catalogue.get(intervention_id)
        policy_item = policy.get(intervention_id)
        rejection = rejected.get(intervention_id)
        utility_item = utility.get(intervention_id)
        rows.append({
            "intervention": intervention_id,
            "display_name": definition.display_name if definition else intervention_id.replace("_", " ").title(),
            "generated": intervention_id in generated,
            "cost_level": generated.get(intervention_id, {}).get(
                "cost_level", definition.cost_level if definition else None
            ),
            "intrusiveness": generated.get(intervention_id, {}).get(
                "intrusiveness", definition.intrusiveness if definition else None
            ),
            "policy_status": (
                policy_item.get("status") if policy_item else rejection.get("status")
                if rejection else "NOT_EVALUATED"
            ),
            "policy_reasons": (
                policy_item.get("reasons", []) if policy_item else rejection.get("reasons", [])
                if rejection else []
            ),
            "stopped_at_rule": policy_item.get("stopped_at_rule") if policy_item else None,
            "replacement": policy_item.get("replacement") if policy_item else None,
            "utility_score": utility_item.get("score") if utility_item else None,
            "utility_breakdown": utility_item.get("score_breakdown", {}) if utility_item else {},
            "confidence": utility_item.get("confidence") if utility_item else None,
            "channel": utility_item.get("channel") if utility_item else None,
            "selected": intervention_id == trace.selected_intervention,
            "explanation": rejection.get("statement") if rejection else None,
        })
    return rows


def decision_trace(decision_id: str, db: Session) -> dict[str, Any] | None:
    trace = db.get(DecisionTrace, decision_id)
    if trace is None:
        return None
    snapshot = db.get(SessionFeatureSnapshot, trace.feature_snapshot_id) if trace.feature_snapshot_id else None
    explanation = trace.explanation
    candidates = _candidate_rows(trace, db)
    rejected = explanation.get("rejected", [])
    discount = next(
        (item for item in rejected if item.get("intervention") == "LIMITED_TIME_DISCOUNT"),
        None,
    )
    return {
        "decision_id": trace.decision_id,
        "session_id": trace.session_id,
        "trace_id": trace.trace_id,
        "decision_time": _iso(trace.decision_time),
        "trigger": trace.trigger,
        "risk": {
            "probability": trace.abandonment_probability,
            "band": trace.risk_band,
            "model_version": trace.model_versions.get("risk"),
            "statement": explanation.get("risk", {}).get("statement"),
        },
        "root_causes": trace.root_causes,
        "candidates": candidates,
        "policy_results": trace.policy_results,
        "utility_scores": trace.utility_scores,
        "final": {
            "decision": trace.decision,
            "selected_intervention": trace.selected_intervention,
            "channel": trace.channel,
            "confidence": trace.recommendation_confidence,
        },
        "explanation": explanation,
        "feature_snapshot": ({
            "snapshot_id": snapshot.snapshot_id,
            "computed_at": _iso(snapshot.computed_at),
            "feature_schema_version": snapshot.feature_schema_version,
            "features": snapshot.features,
            "trigger_event_id": snapshot.trigger_event_id,
        } if snapshot else None),
        "model_versions": trace.model_versions,
        "latency_ms": trace.latency_ms,
        "outcome": _outcome_summary(db, trace.decision_id),
        "audit_answers": {
            "elevated_risk": explanation.get("risk", {}).get("statement"),
            "root_cause": explanation.get("inference", {}).get("statement"),
            "selected_intervention": explanation.get("action", {}).get("statement"),
            "rejected_interventions": [item.get("statement") for item in rejected],
            "discount_not_offered": (
                discount.get("statement") if discount else "A discount was selected."
            ),
            "uncertainty": explanation.get("uncertainty", {}).get("statement"),
            "versions": trace.model_versions,
        },
    }


def model_metrics(db: Session) -> dict[str, Any]:
    models = list(db.scalars(
        select(ModelRegistry)
        .order_by(ModelRegistry.model_type, ModelRegistry.status, ModelRegistry.trained_at.desc())
    ))
    return {
        "models": [
            {
                "model_id": model.model_id,
                "model_name": model.model_name,
                "model_version": model.model_version,
                "model_type": model.model_type,
                "status": model.status,
                "feature_schema_version": model.feature_schema_version,
                "training_data_version": model.training_data_version,
                "trained_at": _iso(model.trained_at),
                "promoted_at": _iso(model.promoted_at),
                "metrics": model.metrics,
                "notes": model.notes,
            }
            for model in models
        ],
        "count": len(models),
        "generated_at": _iso(datetime.now(timezone.utc)),
    }
