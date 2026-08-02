from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from sqlalchemy.orm import Session

from backend import config
from backend.domain.enums import CostLevel, Decision
from backend.domain.interventions import InterventionDefinition, InterventionId
from backend.explainability.structured import build_explanation, intervention_payload
from backend.feature_engine.compute import compute_features
from backend.feature_engine.schema import FEATURE_SCHEMA_VERSION
from backend.policy_engine.engine import (
    PolicyResult,
    approved_candidates,
    evaluate_all,
    finalize_discount_protection,
)
from backend.recommendation.candidates import generate_candidates
from backend.recommendation.ranker import ScoredIntervention, score_all
from backend.risk_model.predict import predict as predict_risk
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause import stub as root_cause_model
from backend.root_cause.contracts import CauseResult
from backend.session_state.cache import cache_session_state
from backend.session_state.rebuild import rebuild_from_events
from backend.session_state.state import SessionState
from backend.storage.repositories import user_history
from backend.storage.session_store import SessionStore

from .triggers import TriggerVerdict, evaluate


@dataclass(frozen=True, slots=True)
class DecisionRun:
    response: dict[str, object]
    state: SessionState
    features: dict[str, float]
    risk: RiskPrediction | None
    causes: CauseResult | None
    candidates: tuple[InterventionDefinition, ...]
    policy_results: tuple[PolicyResult, ...]
    ranked: tuple[ScoredIntervention, ...]
    trace_id: str
    trigger: str
    trigger_event_id: str | None
    decision_time: datetime
    should_persist: bool = True


def _suppressed(
    *,
    state: SessionState,
    features: dict[str, float],
    verdict: TriggerVerdict,
    trace_id: str,
    trigger: str,
    decision_time: datetime,
) -> DecisionRun:
    cached = dict(state.last_decision.get("response", {})) if state.last_decision else {}
    cached.update({
        "session_id": state.session_id,
        "suppressed": True,
        "suppression_reason": verdict.reason,
        "retry_after_seconds": verdict.retry_after_seconds,
    })
    return DecisionRun(
        response=cached,
        state=state,
        features=features,
        risk=None,
        causes=None,
        candidates=(),
        policy_results=(),
        ranked=(),
        trace_id=trace_id,
        trigger=trigger,
        trigger_event_id=verdict.trigger_event_id,
        decision_time=decision_time,
        should_persist=False,
    )


def _select(
    ranked: tuple[ScoredIntervention, ...],
    causes: CauseResult,
) -> tuple[Decision, ScoredIntervention | None]:
    top = ranked[0] if ranked else None
    if top is None or top.candidate.intervention_id == InterventionId.NO_ACTION:
        return (Decision.ABSTAIN if causes.abstained else Decision.NO_ACTION), top
    if top.confidence < config.MIN_RECOMMENDATION_CONFIDENCE:
        return (Decision.ABSTAIN if causes.abstained else Decision.NO_ACTION), None
    if (
        top.confidence < config.PERSONALIZED_CONFIDENCE
        and top.candidate.cost_level not in (CostLevel.ZERO, CostLevel.LOW)
    ):
        safe = next(
            (
                item
                for item in ranked
                if item.candidate.cost_level in (CostLevel.ZERO, CostLevel.LOW)
                and item.candidate.intervention_id != InterventionId.NO_ACTION
                and item.score >= 0
            ),
            None,
        )
        return (Decision.INTERVENE, safe) if safe else (Decision.NO_ACTION, None)
    return Decision.INTERVENE, top


def run_decision(
    session_id: str,
    trigger: str,
    db: Session,
    store: SessionStore,
    *,
    force: bool = False,
    now: datetime | None = None,
) -> DecisionRun:
    started = perf_counter()
    decision_time = now or datetime.now(timezone.utc)
    trace_id = f"tr_{uuid4().hex}"
    state = store.get(f"session:{session_id}:state")
    if not isinstance(state, SessionState):
        state = rebuild_from_events(session_id, db)
        cache_session_state(store, state)

    feature_started = perf_counter()
    features = compute_features(state, user_history(db, state.user_id, as_of=decision_time))
    timings = {"features": round((perf_counter() - feature_started) * 1_000, 3)}
    verdict = evaluate(state, trigger, features, force=force, now=decision_time)
    if not verdict.should_decide:
        return _suppressed(
            state=state,
            features=features,
            verdict=verdict,
            trace_id=trace_id,
            trigger=trigger,
            decision_time=decision_time,
        )

    risk = predict_risk(features)
    timings["risk"] = risk.latency_ms
    if risk.model_version == "risk-unavailable":
        causes = CauseResult.unknown(model_version="cause-unavailable")
    elif risk.probability < config.RISK_INTERVENTION_THRESHOLD:
        causes = CauseResult((), "cause-stub-v1", False, 0.0, 0.0)
    else:
        causes = root_cause_model.predict(features)
    timings["root_cause"] = causes.latency_ms

    policy_started = perf_counter()
    candidates = generate_candidates(causes, features)
    policy_results = evaluate_all(
        candidates, state, features, risk, causes, now=decision_time
    )
    ranked = score_all(
        approved_candidates(policy_results),
        features,
        risk,
        causes,
        current_route=state.current_route,
    )
    policy_results = finalize_discount_protection(policy_results, ranked)
    ranked = score_all(
        approved_candidates(policy_results),
        features,
        risk,
        causes,
        current_route=state.current_route,
    )
    timings["policy_and_rank"] = round((perf_counter() - policy_started) * 1_000, 3)
    decision, selected = _select(ranked, causes)

    decision_id = f"D-{uuid4().hex}"
    explanation_started = perf_counter()
    explanation = build_explanation(
        decision_id=decision_id,
        features=features,
        risk=risk,
        causes=causes,
        policy_results=policy_results,
        ranked=ranked,
        selected=selected,
        decision=decision,
    )
    timings["explain"] = round((perf_counter() - explanation_started) * 1_000, 3)
    recommended = intervention_payload(selected)
    if recommended is None:
        recommended = {
            "type": InterventionId.NO_ACTION.value,
            "channel": None,
            "reason": explanation["action"]["statement"],
            "confidence": 0.0,
        }
    else:
        recommended["decision_id"] = decision_id
        if selected and selected.candidate.intervention_id == InterventionId.LIMITED_TIME_DISCOUNT:
            recommended["discount_pct"] = min(
                config.DEFAULT_DISCOUNT_PCT,
                selected.candidate.max_discount_pct or config.DEFAULT_DISCOUNT_PCT,
            )
    timings["total"] = round((perf_counter() - started) * 1_000, 3)
    response: dict[str, object] = {
        "decision_id": decision_id,
        "session_id": session_id,
        "decision": decision.value,
        "abandonment_probability": risk.probability,
        "risk_level": risk.band.value,
        "root_causes": [item.to_dict() for item in causes.root_causes],
        "recommended_intervention": recommended,
        "evidence": [item["statement"] for item in explanation["observations"]],
        "confidence_score": selected.confidence if selected else 0.0,
        "intervention_cost": (
            selected.candidate.cost_level.value if selected else CostLevel.ZERO.value
        ),
        "policy_results": [result.to_dict() for result in policy_results],
        "utility_scores": [item.to_dict() for item in ranked],
        "explanation": explanation,
        "latency_ms": timings,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "suppressed": False,
    }
    state.last_decision = {
        "decision_id": decision_id,
        "at": decision_time.isoformat(),
        "feature_hash": verdict.feature_hash,
        "response": response,
    }
    cache_session_state(store, state)
    return DecisionRun(
        response=response,
        state=state,
        features=features,
        risk=risk,
        causes=causes,
        candidates=candidates,
        policy_results=policy_results,
        ranked=ranked,
        trace_id=trace_id,
        trigger=trigger,
        trigger_event_id=verdict.trigger_event_id,
        decision_time=decision_time,
    )
