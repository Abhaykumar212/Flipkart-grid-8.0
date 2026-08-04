from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from sqlalchemy.orm import Session

from backend import config
from backend.agents.reasoning import Diagnosis, diagnose, endorsed_candidates
from backend.domain.causes import RootCause
from backend.domain.enums import Channel, CostLevel, Decision, RiskBand
from backend.domain.interventions import InterventionDefinition, InterventionId
from backend.explainability.structured import build_explanation, intervention_payload
from backend.experimentation.assign import active_experiment, get_or_assign
from backend.feature_engine.compute import compute_features
from backend.feature_engine.schema import FEATURE_SCHEMA_VERSION
from backend.policy_engine.browsing import is_browsing_assist
from backend.policy_engine.engine import (
    PolicyResult,
    approved_candidates,
    evaluate_all,
    finalize_discount_protection,
)
from backend.recommendation.candidates import generate_candidates
from backend.recommendation.catalogue import CATALOGUE_BY_ID, INTERVENTION_CATALOGUE
from backend.recommendation.ranker import ScoredIntervention, score_all
from backend.observability.drift import drift_monitor
from backend.observability.latency import metrics_registry
from backend.risk_model.predict import predict as predict_risk
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.predict import predict as predict_root_causes
from backend.root_cause.contracts import CausePrediction, CauseResult
from backend.review_intelligence.cache import summary_available
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
    experiment_id: str | None = None
    experiment_group: str | None = None
    diagnosis: Diagnosis | None = None


def _top_attributions(
    risk: RiskPrediction,
    features: dict[str, float],
    limit: int = 12,
) -> list[dict[str, object]]:
    """Signed SHAP for the strongest drivers, for the live inspector.

    `explanation.observations` carries only what the narrative needed; the UI
    wants a wider view of what actually moved the score.
    """
    ranked = sorted(
        risk.shap_by_feature.items(), key=lambda item: abs(item[1]), reverse=True
    )[:limit]
    return [
        {
            "feature": name,
            "value": round(float(features.get(name, 0.0)), 4),
            "shap": round(float(shap), 6),
        }
        for name, shap in ranked
    ]


def _suppressed(
    *,
    state: SessionState,
    features: dict[str, float],
    verdict: TriggerVerdict,
    trace_id: str,
    trigger: str,
    decision_time: datetime,
) -> DecisionRun:
    metrics_registry.increment("decision_suppressions", label=verdict.reason)
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


def _subtle(ranked: tuple[ScoredIntervention, ...]) -> ScoredIntervention | None:
    """Best candidate that is cheap and quiet enough to show unprompted."""
    return next(
        (
            item
            for item in ranked
            if item.score >= 0
            and item.candidate.intervention_id != InterventionId.NO_ACTION
            and item.candidate.cost_level in (CostLevel.ZERO, CostLevel.LOW)
            and item.candidate.intrusiveness <= 1
        ),
        None,
    )


def _select(
    ranked: tuple[ScoredIntervention, ...],
    causes: CauseResult,
    risk: RiskPrediction | None = None,
    features: dict[str, float] | None = None,
) -> tuple[Decision, ScoredIntervention | None]:
    risk = risk or RiskPrediction(
        config.RISK_HIGH_THRESHOLD,
        0.0,
        RiskBand.HIGH,
        "selection-test",
        (),
        0.0,
    )
    if risk.probability < config.RISK_INTERVENTION_THRESHOLD:
        # Below the floor the only thing that earns an action is visible
        # deliberation with an empty cart, and then only a quiet one.
        if features is not None and is_browsing_assist(features):
            helpful = _subtle(ranked)
            return (Decision.INTERVENE, helpful) if helpful else (Decision.NO_ACTION, None)
        return Decision.NO_ACTION, None
    top = ranked[0] if ranked else None
    if top is None or top.candidate.intervention_id == InterventionId.NO_ACTION:
        return (Decision.ABSTAIN if causes.abstained else Decision.NO_ACTION), top
    if top.confidence < config.MIN_RECOMMENDATION_CONFIDENCE:
        return (Decision.ABSTAIN if causes.abstained else Decision.NO_ACTION), None

    # Medium-risk sessions only receive a subtle inline action, even when the
    # cause is strong. This is the fifth row of the frozen confidence table.
    if risk.probability < config.RISK_HIGH_THRESHOLD:
        subtle = _subtle(ranked)
        return (Decision.INTERVENE, subtle) if subtle else (Decision.NO_ACTION, None)

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


def _control_arm(
    *,
    risk: RiskPrediction,
    features: dict[str, float],
    state: SessionState,
) -> tuple[CauseResult, tuple[InterventionDefinition, ...], tuple[PolicyResult, ...], tuple[ScoredIntervention, ...], Decision, ScoredIntervention | None]:
    causes = CauseResult(
        (
            CausePrediction(
                RootCause.LOW_PURCHASE_INTENT,
                0.55,
                ("experiment_control",),
            ),
        ),
        "control-skipped-v1",
        False,
        0.55,
        0.0,
    )
    if risk.probability < config.RISK_INTERVENTION_THRESHOLD:
        return causes, (), (), (), Decision.NO_ACTION, None
    candidate = CATALOGUE_BY_ID[InterventionId.WISHLIST_REMINDER]
    candidates = (candidate,)
    policy_results = evaluate_all(candidates, state, features, risk, causes)
    if not approved_candidates(policy_results):
        return causes, candidates, policy_results, (), Decision.NO_ACTION, None
    ranked = (
        ScoredIntervention(
            candidate=candidate,
            score=0.01,
            confidence=max(config.MIN_RECOMMENDATION_CONFIDENCE, 0.56),
            score_breakdown={
                "relevance": 0.0,
                "expected_uplift": 0.0,
                "user_affinity": 0.0,
                "information_gain": 0.0,
                "direct_cost_penalty": 0.0,
                "margin_risk_penalty": 0.0,
                "fatigue_penalty": 0.0,
                "intrusiveness_penalty": 0.0,
            },
            channel=Channel.BANNER,
            relevant_cause=None,
            evidence_keys=(),
        ),
    )
    return causes, candidates, policy_results, ranked, Decision.INTERVENE, ranked[0]


def run_decision(
    session_id: str,
    trigger: str,
    db: Session,
    store: SessionStore,
    *,
    force: bool = False,
    now: datetime | None = None,
    language: str = "en",
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
    drift_monitor.record(features, risk.probability)
    timings["risk"] = risk.latency_ms
    diagnosis: Diagnosis | None = None
    reasoning_path = "model:not_attempted"
    experiment_id = None
    experiment_group = None
    experiment = active_experiment(db)
    if experiment is not None:
        assignment = get_or_assign(db, session_id, experiment, now=decision_time)
        experiment_id = assignment.experiment_id
        experiment_group = assignment.group_name

    if experiment is not None and experiment_group == experiment.control_group:
        causes, candidates, policy_results, ranked, decision, selected = _control_arm(
            risk=risk,
            features=features,
            state=state,
        )
        timings["root_cause"] = causes.latency_ms
        timings["policy_and_rank"] = 0.0
    elif risk.model_version == "risk-unavailable":
        causes = CauseResult.unknown(model_version="cause-unavailable")
        timings["root_cause"] = causes.latency_ms
        candidates = ()
        policy_results = ()
        ranked = ()
        timings["policy_and_rank"] = 0.0
        decision, selected = Decision.ABSTAIN, None
    else:
        # The reasoning agent gets the model's probability and its full SHAP
        # attribution and decides the cause. The trained cause model is what
        # answers when the agent can't — no key, rate limited, budget spent.
        if (
            risk.probability < config.RISK_INTERVENTION_THRESHOLD
            and not is_browsing_assist(features)
        ):
            causes = CauseResult((), "cause-stub-v1", False, 0.0, 0.0)
        else:
            diagnosis, reasoning_path = diagnose(
                session_id,
                state,
                features,
                risk,
                force=force,
                now=decision_time.timestamp(),
            )
            causes = diagnosis.causes if diagnosis else predict_root_causes(features)
        timings["root_cause"] = causes.latency_ms

        policy_started = perf_counter()
        product_ids = tuple(
            str(item.get("product_id"))
            for item in state.cart.get("items", [])
            if isinstance(item, dict) and item.get("product_id")
        )
        if not product_ids and state.current_product_id:
            product_ids = (state.current_product_id,)
        policy_features = dict(features)
        policy_features["review_summary_available"] = float(
            summary_available(db, product_ids)
        )
        candidates = generate_candidates(causes, features)
        if diagnosis is not None:
            # The agent may back a lever whose catalogue entry doesn't list the
            # cause it diagnosed. That's a judgement call worth honouring, so the
            # pick joins the pool — policy still decides whether it may run.
            wanted = {item.intervention_id for item in candidates}
            wanted.update(endorsed_candidates(diagnosis.endorsements))
            candidates = tuple(
                item
                for item in INTERVENTION_CATALOGUE
                if item.is_active and item.intervention_id in wanted
            )
        endorsements = diagnosis.endorsements if diagnosis else None
        avoid = diagnosis.avoid if diagnosis else None
        policy_results = evaluate_all(
            candidates, state, policy_features, risk, causes, now=decision_time
        )
        ranked = score_all(
            approved_candidates(policy_results),
            features,
            risk,
            causes,
            current_route=state.current_route,
            endorsements=endorsements,
            avoid=avoid,
        )
        policy_results = finalize_discount_protection(policy_results, ranked)
        ranked = score_all(
            approved_candidates(policy_results),
            features,
            risk,
            causes,
            current_route=state.current_route,
            endorsements=endorsements,
            avoid=avoid,
        )
        timings["policy_and_rank"] = round((perf_counter() - policy_started) * 1_000, 3)
        decision, selected = _select(ranked, causes, risk, features)
    product_ids = tuple(
        str(item.get("product_id"))
        for item in state.cart.get("items", [])
        if isinstance(item, dict) and item.get("product_id")
    )
    if not product_ids and state.current_product_id:
        product_ids = (state.current_product_id,)

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
        language=language,
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
        if selected and selected.candidate.intervention_id == InterventionId.REVIEW_SUMMARY:
            recommended["review_product_id"] = product_ids[0] if product_ids else None
        if selected and selected.candidate.intervention_id == InterventionId.LIMITED_TIME_DISCOUNT:
            recommended["discount_pct"] = min(
                config.DEFAULT_DISCOUNT_PCT,
                selected.candidate.max_discount_pct or config.DEFAULT_DISCOUNT_PCT,
            )
    timings["total"] = round((perf_counter() - started) * 1_000, 3)
    metrics_registry.increment("decisions", label=decision.value)
    for result in policy_results:
        for reason in result.reasons:
            metrics_registry.increment("policy_rejections", label=reason.value)
    for stage, latency in timings.items():
        metrics_registry.observe(f"decision_{stage}", latency)
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
        "reasoning": (
            diagnosis.to_dict() if diagnosis else {"path": reasoning_path}
        ),
        "shap_attributions": _top_attributions(risk, features),
        "latency_ms": timings,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "experiment_group": experiment_group,
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
        experiment_id=experiment_id,
        experiment_group=experiment_group,
        diagnosis=diagnosis,
    )
