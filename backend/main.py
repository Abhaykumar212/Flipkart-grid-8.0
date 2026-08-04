"""FastAPI inference service for cart-abandonment prediction."""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = PROJECT_ROOT / "ml" / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "model.joblib"
CALIBRATOR_PATH = ARTIFACT_DIR / "calibrator.joblib"
EXPLAINER_PATH = ARTIFACT_DIR / "explainer.joblib"
FEATURE_NAMES_PATH = ARTIFACT_DIR / "feature_names.json"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"

# Add project root to path so we can import the ml package
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.feature_engineering import (  # noqa: E402
    ALL_FEATURE_NAMES,
    RAW_FEATURE_NAMES,
    engineer_features,
)

from . import config, db, ledger, reservations  # noqa: E402
from .agents import browsing_intent, companion_chat, critic, explanation_scorer, gate, intervention, reengagement, root_cause  # noqa: E402
from .agents.memory import memory_store  # noqa: E402
from .schemas import (  # noqa: E402
    CartAddRequest,
    CartContext,
    CompanionChatRequest,
    CompanionChatResponse,
    DeliveryDecisionRequest,
    ElicitationResponseRequest,
    GateDecision,
    InterventionPlan,
    PrimaryRootCause,
    ProductAvailability,
    RootCauseAnalysis,
    RootCauseResponse,
    SessionLedgerResponse,
    ShopperProfile,
    TraceSpan,
)
from .trace import Stage, Status, TraceRecorder  # noqa: E402

MODEL: Any = None
CALIBRATOR: Any = None
EXPLAINER: Any = None
FEATURE_NAMES: list = []


class SessionFeatures(BaseModel):
    """The 22 observable signals a live session can supply.

    Bounds mirror the training distribution; the frontend clamps to the same
    ranges so inference never sees values the model was not trained on.
    """

    model_config = ConfigDict(extra="forbid")

    # A. Cart engagement
    seconds_spent_in_cart: float = Field(ge=0.0, le=900.0)
    times_returned_to_product_page: int = Field(ge=0, le=10)
    product_reviews_read: int = Field(ge=0, le=8)
    seconds_idle_before_checkout: float = Field(ge=0.0, le=300.0)
    delivery_pincode_checks: int = Field(ge=0, le=5)
    saved_items_in_wishlist: int = Field(ge=0, le=20)

    # B. Cost friction
    cart_value_vs_typical_order: float = Field(ge=0.0, le=6.0)
    delivery_fee_percent_of_cart: float = Field(ge=0.0, le=25.0)
    price_dropped_since_first_view: int = Field(ge=0, le=1)
    discount_seeking_tendency: float = Field(ge=0.0, le=1.0)
    failed_coupon_attempts: int = Field(ge=0, le=6)

    # C. Delivery friction
    estimated_delivery_days: int = Field(ge=1, le=10)

    # D. Checkout & trust friction
    payment_method_on_file: int = Field(ge=0, le=1)
    checkout_steps_completed: int = Field(ge=0, le=3)
    payment_attempts_failed: int = Field(ge=0, le=5)
    is_guest_checkout: int = Field(ge=0, le=1)

    # E. Customer history
    past_abandonment_rate: float = Field(ge=0.0, le=1.0)
    past_order_return_rate: float = Field(ge=0.0, le=0.5)
    lifetime_orders_placed: int = Field(ge=0, le=120)
    days_since_last_purchase: float = Field(ge=0.0, le=400.0)

    # F. Session context
    is_mobile_session: int = Field(ge=0, le=1)
    is_late_night_session: int = Field(ge=0, le=1)


class RootCauseRequest(BaseModel):
    """Everything the Phase 2 agent needs: the model inputs plus real cart state."""

    model_config = ConfigDict(extra="forbid")

    features: SessionFeatures
    cart_context: CartContext = Field(default_factory=CartContext)
    shopper_profile: ShopperProfile = Field(default_factory=ShopperProfile)
    # Stable per-browser-session id, used for dedup and budget accounting.
    session_id: str = "anonymous"
    # Manual "Re-run analysis" bypasses dedup/cooldown but not the session cap.
    force: bool = False


class InterventionFeedback(BaseModel):
    """Shopper response to a surfaced intervention, from the companion widget."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    lever_id: str
    action: Literal["accepted", "dismissed", "converted"]
    # Delivery-layer context, optional so older clients still validate. Recorded
    # alongside the response so the ledger can attribute an outcome to the rung
    # and surface it was actually spent on.
    intensity_rung: Optional[int] = None
    surface: Optional[str] = None
    root_cause: Optional[str] = None
    confidence: Optional[str] = None


class FeatureContribution(BaseModel):
    feature: str
    shap_value: float


class PredictionResponse(BaseModel):
    abandonment_probability: float
    confidence_score: float
    risk_tier: Literal["low", "medium", "high"]
    top_contributing_features: list
    feature_impacts: dict
    status: Literal["success"] = "success"


def _load_artifacts() -> None:
    global MODEL, CALIBRATOR, EXPLAINER, FEATURE_NAMES

    missing = [
        str(path)
        for path in (MODEL_PATH, EXPLAINER_PATH, FEATURE_NAMES_PATH)
        if not path.exists()
    ]
    if missing:
        raise RuntimeError(
            "Required ML artifacts are missing: "
            + ", ".join(missing)
            + ". Run 'python ml/generate_dataset.py' and "
            "'python ml/train_model.py' first."
        )

    MODEL = joblib.load(MODEL_PATH)
    EXPLAINER = joblib.load(EXPLAINER_PATH)
    # May legitimately be None: training only keeps a calibrator when it
    # measurably improved held-out log-loss.
    CALIBRATOR = joblib.load(CALIBRATOR_PATH) if CALIBRATOR_PATH.exists() else None
    FEATURE_NAMES = json.loads(FEATURE_NAMES_PATH.read_text(encoding="utf-8"))
    if len(FEATURE_NAMES) != len(ALL_FEATURE_NAMES):
        raise RuntimeError(
            f"feature_names.json must contain exactly {len(ALL_FEATURE_NAMES)} "
            f"features, got {len(FEATURE_NAMES)}"
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    _load_artifacts()
    # Eager, so a fresh clone with an unwritable backend/data/ fails at boot
    # rather than on the first gate evaluation.
    db.init_schema(db.get_db())
    yield


app = FastAPI(
    title="Flipkart GRiD 8.0 Cart-Abandonment Prediction API",
    description="Calibrated XGBoost abandonment probability with SHAP attribution.",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "online",
        "model": "XGBoost",
        "explainer": "SHAP TreeExplainer",
        "raw_feature_count": len(RAW_FEATURE_NAMES),
        "total_feature_count": len(FEATURE_NAMES),
        "calibrated": CALIBRATOR is not None,
    }


@app.get("/metrics")
def metrics() -> dict:
    """Holdout evaluation of the deployed artifact, including the Bayes ceiling."""
    if not METRICS_PATH.exists():
        raise HTTPException(status_code=404, detail="metrics.json not found")
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def _risk_tier(probability: float) -> str:
    if probability >= 0.80:
        return "high"
    if probability >= 0.60:
        return "medium"
    return "low"


def _extract_shap_values(frame: pd.DataFrame) -> np.ndarray:
    explanation = EXPLAINER(frame)
    values = np.asarray(explanation.values, dtype=float)

    # SHAP versions may represent binary outputs as (rows, features) or
    # (rows, features, classes). Class index 1 is abandonment when present.
    if values.ndim == 3:
        values = values[:, :, 1]
    if values.ndim != 2 or values.shape != (1, len(FEATURE_NAMES)):
        raise ValueError(f"Unexpected SHAP output shape: {values.shape}")
    return values[0]


def _run_inference(
    payload: SessionFeatures, recorder: TraceRecorder
) -> Tuple[PredictionResponse, Dict[str, float]]:
    """Feature engineering -> model -> SHAP, emitting a span per stage.

    Shared by the prediction endpoint and the root-cause endpoint so both agree
    exactly on the numbers, and so the console shows the same stages either way.
    """
    values = payload.model_dump()

    with recorder.span(Stage.FEATURE_ENGINEERING, "Engineer features") as span:
        raw_frame = pd.DataFrame(
            [[values[name] for name in RAW_FEATURE_NAMES]],
            columns=RAW_FEATURE_NAMES,
        )
        frame = engineer_features(raw_frame)
        span["detail"] = {
            "raw_features": len(RAW_FEATURE_NAMES),
            "engineered_features": len(FEATURE_NAMES) - len(RAW_FEATURE_NAMES),
            "total_features": len(FEATURE_NAMES),
            "engineered_values": {
                name: round(float(frame.iloc[0][name]), 4)
                for name in FEATURE_NAMES[len(RAW_FEATURE_NAMES):]
            },
        }

    with recorder.span(Stage.MODEL_INFERENCE, "XGBoost inference") as span:
        probability = float(MODEL.predict_proba(frame)[0, 1])
        if CALIBRATOR is not None:
            probability = float(CALIBRATOR.predict([probability])[0])
        confidence = abs(probability - 0.5) * 2.0
        tier = _risk_tier(probability)
        span["detail"] = {
            "abandonment_probability": round(probability, 6),
            "risk_tier": tier,
            "confidence": round(confidence, 6),
            "calibrator_applied": CALIBRATOR is not None,
            "trees": int(getattr(MODEL, "n_estimators", 0) or 0),
        }

    with recorder.span(Stage.SHAP_ATTRIBUTION, "SHAP attribution") as span:
        shap_values = _extract_shap_values(frame)
        # `zip(..., strict=True)` needs Python 3.10+; this service targets 3.9.
        # The length invariant is already enforced by the shape check above.
        feature_impacts = {
            name: round(float(impact), 6)
            for name, impact in zip(FEATURE_NAMES, shap_values)
        }
        positive_indices = np.flatnonzero(shap_values > 0.0)
        ordered_positive = positive_indices[
            np.argsort(shap_values[positive_indices])[::-1]
        ][:3]
        top_features = [
            FeatureContribution(
                feature=FEATURE_NAMES[int(index)],
                shap_value=round(float(shap_values[int(index)]), 6),
            )
            for index in ordered_positive
        ]
        span["detail"] = {
            "top_positive_drivers": [
                {"feature": f.feature, "shap_value": f.shap_value} for f in top_features
            ],
            "attributed_features": len(feature_impacts),
        }

    response = PredictionResponse(
        abandonment_probability=round(probability, 6),
        confidence_score=round(confidence, 6),
        risk_tier=tier,
        top_contributing_features=top_features,
        feature_impacts=feature_impacts,
        status="success",
    )
    return response, values


@app.post("/api/predict-abandonment", response_model=PredictionResponse)
def predict_abandonment(payload: SessionFeatures) -> PredictionResponse:
    if MODEL is None or EXPLAINER is None:
        raise HTTPException(status_code=503, detail="ML artifacts are not loaded")

    try:
        prediction, _ = _run_inference(payload, TraceRecorder())
        return prediction
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Inference failed: {error}") from error


@app.get("/api/pipeline-config")
def pipeline_config() -> dict:
    """Trigger policy and agent configuration, for display in the console."""
    return {
        "rca_threshold": config.RCA_PROBABILITY_THRESHOLD,
        "min_cart_age_seconds": config.RCA_MIN_CART_AGE_SECONDS,
        "cooldown_seconds": config.RCA_COOLDOWN_SECONDS,
        "max_per_session": config.RCA_MAX_PER_SESSION,
        "rca_model": config.RCA_MODEL,
        "rca_fallback_model": config.RCA_FALLBACK_MODEL,
        "reasoning_effort": config.RCA_REASONING_EFFORT,
        "llm_provider": config.LLM_PROVIDER,
        "llm_configured": config.llm_is_configured(),
        "risk_tiers": {"high": 0.80, "medium": 0.60},
    }


@app.post("/api/root-cause-analysis", response_model=RootCauseResponse)
def root_cause_analysis(payload: RootCauseRequest) -> RootCauseResponse:
    """Phase 2: diagnose *why* an at-risk cart is at risk.

    Re-runs inference server-side rather than trusting a client-supplied
    probability, so the gate decision cannot be spoofed from the browser and the
    analysis is always grounded in freshly computed SHAP values.
    """
    if MODEL is None or EXPLAINER is None:
        raise HTTPException(status_code=503, detail="ML artifacts are not loaded")

    recorder = TraceRecorder()
    cart = payload.cart_context

    try:
        prediction, feature_values = _run_inference(payload.features, recorder)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Inference failed: {error}") from error

    signature = root_cause.build_feature_signature(feature_values)

    with recorder.span(Stage.RISK_GATE, "Evaluate trigger policy") as span:
        decision = gate.evaluate(
            probability=prediction.abandonment_probability,
            cart_age_seconds=cart.cart_age_seconds,
            signature=signature,
            session_id=payload.session_id,
            store=gate.gate_store,
            force=payload.force,
        )
        span["status"] = Status.OK if decision.fired else Status.SKIPPED
        span["detail"] = {
            "fired": decision.fired,
            "reason": decision.reason,
            "signature": signature,
            **decision.checks,
        }

    gate_model = GateDecision(
        fired=decision.fired,
        threshold=decision.threshold,
        reason=decision.reason,
        checks=decision.checks,
    )

    def envelope(status: str, analysis=None, plan=None, meta=None, message=None) -> RootCauseResponse:
        meta = meta or {}
        return RootCauseResponse(
            pipeline_run_id=recorder.run_id,
            status=status,
            prediction=prediction.model_dump(),
            gate=gate_model,
            analysis=analysis,
            intervention_plan=plan,
            model_used=meta.get("model_used"),
            latency_ms=meta.get("latency_ms", 0.0),
            message=message,
            trace=[TraceSpan(**span) for span in recorder.spans],
        )

    if not decision.fired:
        return envelope("gate_not_met", message=decision.reason)

    if not config.llm_is_configured():
        hint = config.missing_key_hint()
        recorder.add(
            Stage.ROOT_CAUSE_AGENT,
            f"Skipped — {hint} not configured",
            status=Status.SKIPPED,
            detail={"hint": f"Set {hint} in .env (see .env.example)"},
        )
        return envelope(
            "not_configured",
            message=f"{hint} is not set; copy .env.example to .env and add a key.",
        )

    analysis, meta = root_cause.analyse(
        probability=prediction.abandonment_probability,
        risk_tier=prediction.risk_tier,
        confidence=prediction.confidence_score,
        features=feature_values,
        feature_impacts=prediction.feature_impacts,
        cart=cart,
        recorder=recorder,
    )

    if analysis is None:
        status = "rate_limited" if meta.get("rate_limited") else "error"
        return envelope(status, meta=meta, message=meta.get("error", "Analysis failed"))

    gate.gate_store.record_run(payload.session_id, signature)

    with recorder.span(Stage.INTERVENTION_RANKING, "Rank interventions") as span:
        plan = intervention.build_intervention_plan(
            analysis=analysis,
            probability=prediction.abandonment_probability,
            shopper_profile=payload.shopper_profile,
            session_id=payload.session_id,
            memory=memory_store,
        )
        span["detail"] = {
            "top_lever_ids": [item.lever_id for item in plan.top_interventions],
            "top_scores": [item.score for item in plan.top_interventions],
            "fallback_lever_id": plan.fallback_intervention.lever_id if plan.fallback_intervention else None,
            "excluded_lever_ids": plan.excluded_lever_ids,
            "reservation": _hold_stock(payload, prediction.abandonment_probability, analysis),
        }

    verdict = critic.review(analysis, plan, recorder)
    connection = db.get_db()
    for lever_id, reason in verdict.rejected:
        ledger.record_critic_rejection(
            connection,
            session_id=payload.session_id,
            lever_id=lever_id,
            reason=reason,
            root_cause=analysis.primary_root_cause.category,
        )

    if verdict.approved_lever_id is None:
        # No lever survived, so this run's verdict is "do nothing" — written
        # through the same path as every other hold, because the delivery layer
        # never sees this run and will not report one of its own.
        detail = "; ".join(f"{lever_id}: {reason}" for lever_id, reason in verdict.rejected)
        ledger.record_decision(
            connection,
            DeliveryDecisionRequest(
                session_id=payload.session_id,
                outcome="held",
                reason="critic_rejected",
                detail=detail,
                root_cause=analysis.primary_root_cause.category,
                probability=prediction.abandonment_probability,
            ),
        )
        return envelope(
            "critic_blocked",
            analysis=analysis,
            meta=meta,
            message="Critic rejected every ranked lever as misaligned with the diagnosed cause.",
        )

    evidence = root_cause.build_evidence(feature_values, prediction.feature_impacts)
    explanation_result = explanation_scorer.score(analysis, evidence, recorder)
    ledger.annotate_latest_event(
        connection,
        session_id=payload.session_id,
        lever_id=verdict.approved_lever_id,
        action="shown",
        explanation_verdict=explanation_result.verdict,
    )

    return envelope(
        "success",
        analysis=analysis,
        plan=_approved_plan(plan, verdict.approved_lever_id),
        meta=meta,
    )


CHIP_TO_ROOT_CAUSE: Dict[str, str] = {
    "Price": "cost_friction",
    "Trust or quality": "trust_friction",
    "Still comparing": "product_uncertainty",
}


@app.post("/api/elicitation-response", response_model=RootCauseResponse)
def elicitation_response(payload: ElicitationResponseRequest) -> RootCauseResponse:
    """Handle user response to elicitation prompt ("What's holding you back?").

    Skips LLM RCA agent for this turn because the shopper explicitly told us
    the cause, maps the chip to a root cause, runs Phase 3 ranking, passes through
    critic and explanation scorer, and records decision as user-elicited.
    """
    recorder = TraceRecorder()
    category = CHIP_TO_ROOT_CAUSE.get(payload.chip, "cost_friction")
    probability = payload.probability if payload.probability is not None else 0.85

    analysis = RootCauseAnalysis(
        primary_root_cause=PrimaryRootCause(
            category=category,
            headline=f"User-elicited friction: {payload.chip}",
            explanation=f"Shopper selected '{payload.chip}' when asked what was holding them back.",
            supporting_evidence=[],
        ),
        contributing_factors=[],
        shopper_narrative=f"User explicitly indicated '{payload.chip}'.",
        confidence="high",
        confidence_reasoning="Direct user declaration via elicitation prompt.",
        recommended_levers=[],
        levers_to_avoid=[],
    )

    with recorder.span(Stage.INTERVENTION_RANKING, "Rank interventions (elicited)") as span:
        plan = intervention.build_intervention_plan(
            analysis=analysis,
            probability=probability,
            shopper_profile=payload.shopper_profile,
            session_id=payload.session_id,
            memory=memory_store,
        )
        span["detail"] = {
            "top_lever_ids": [item.lever_id for item in plan.top_interventions],
            "top_scores": [item.score for item in plan.top_interventions],
            "fallback_lever_id": plan.fallback_intervention.lever_id if plan.fallback_intervention else None,
            "excluded_lever_ids": plan.excluded_lever_ids,
            "elicited": True,
            "chip": payload.chip,
        }

    verdict = critic.review(analysis, plan, recorder)
    connection = db.get_db()
    for lever_id, reason in verdict.rejected:
        ledger.record_critic_rejection(
            connection,
            session_id=payload.session_id,
            lever_id=lever_id,
            reason=reason,
            root_cause=category,
        )

    if verdict.approved_lever_id is None:
        detail = "; ".join(f"{lever_id}: {reason}" for lever_id, reason in verdict.rejected)
        ledger.record_decision(
            connection,
            DeliveryDecisionRequest(
                session_id=payload.session_id,
                outcome="held",
                reason="critic_rejected",
                detail=detail,
                root_cause=category,
                probability=probability,
            ),
        )
        return RootCauseResponse(
            pipeline_run_id=recorder.run_id,
            status="critic_blocked",
            prediction={"abandonment_probability": probability, "risk_tier": _risk_tier(probability)},
            gate=GateDecision(fired=True, threshold=0.80, reason="user_elicited"),
            analysis=analysis,
            message="Critic rejected every ranked lever.",
            trace=[TraceSpan(**span) for span in recorder.spans],
        )

    explanation_result = explanation_scorer.score(analysis, [], recorder)
    ledger.annotate_latest_event(
        connection,
        session_id=payload.session_id,
        lever_id=verdict.approved_lever_id,
        action="shown",
        explanation_verdict=explanation_result.verdict,
    )

    ledger.record_decision(
        connection,
        DeliveryDecisionRequest(
            session_id=payload.session_id,
            outcome="elicited",
            reason="user_elicited",
            detail=f"User selected '{payload.chip}' chip",
            root_cause=category,
            probability=probability,
            lever_id=verdict.approved_lever_id,
            confidence="high",
        ),
    )

    return RootCauseResponse(
        pipeline_run_id=recorder.run_id,
        status="success",
        prediction={"abandonment_probability": probability, "risk_tier": _risk_tier(probability)},
        gate=GateDecision(fired=True, threshold=0.80, reason="user_elicited"),
        analysis=analysis,
        intervention_plan=_approved_plan(plan, verdict.approved_lever_id),
        trace=[TraceSpan(**span) for span in recorder.spans],
    )



def _approved_plan(plan: InterventionPlan, approved_lever_id: str) -> InterventionPlan:
    """Drop everything the critic rejected, keeping ranked order below it.

    Removed rather than reordered: the delivery layer delivers the first entry
    it can, so a rejected lever left in the list would still reach the shopper.
    """
    kept = [item for item in plan.top_interventions]
    approved_index = next(i for i, item in enumerate(kept) if item.lever_id == approved_lever_id)
    kept = kept[approved_index:]
    rejected_ids = {item.lever_id for item in plan.top_interventions[:approved_index]}
    fallback = plan.fallback_intervention
    return InterventionPlan(
        top_interventions=kept,
        fallback_intervention=None if fallback and fallback.lever_id in rejected_ids else fallback,
        excluded_lever_ids=plan.excluded_lever_ids + sorted(rejected_ids),
    )


def _hold_stock(
    payload: RootCauseRequest, probability: float, analysis
) -> Optional[Dict[str, Any]]:
    """Reserve a unit of the cart's most valuable line while the shopper decides.

    Only for the two diagnoses a hold can actually serve, and only above the RCA
    threshold — checked here rather than inferred from the gate, because a
    forced re-run fires the gate at any probability.
    """
    category = analysis.primary_root_cause.category
    if probability < config.RCA_PROBABILITY_THRESHOLD or category not in reservations.RESERVING_CAUSES:
        return None

    in_stock = [line for line in payload.cart_context.lines if line.in_stock]
    if not in_stock:
        return None

    line = max(in_stock, key=lambda item: item.selling_price * item.quantity)
    created = reservations.reserve(db.get_db(), payload.session_id, line.product_id)
    return {
        "product_id": line.product_id,
        "created": created,
        "hold_seconds": reservations.HOLD_SECONDS,
        "root_cause": category,
    }


@app.post("/api/intervention-feedback")
def intervention_feedback(payload: InterventionFeedback) -> dict:
    """Feedback Agent write path — records the shopper's response so the
    Memory Agent can penalise repeats this session, and so the log accumulates
    the (state, action, reward) trail a future RL policy would train on.
    """
    memory_store.record(payload.session_id, payload.lever_id, payload.action)
    ledger.annotate_latest_event(
        db.get_db(),
        session_id=payload.session_id,
        lever_id=payload.lever_id,
        action=payload.action,
        intensity_rung=payload.intensity_rung,
        surface=payload.surface,
        root_cause=payload.root_cause,
        confidence=payload.confidence,
    )
    return {"status": "recorded"}


@app.post("/api/delivery-decision")
def delivery_decision(payload: DeliveryDecisionRequest) -> dict:
    """Delivery-layer write path — what was shown, or what was deliberately not.

    The client decides this (fatigue budget and intensity ladder are synchronous,
    client-side checks) and reports it here. "Do nothing" is recorded exactly
    like "intervene": the whole point of the ledger is that a held decision is
    evidence of judgement, not an absence of one.
    """
    ledger.record_decision(db.get_db(), payload)
    return {"status": "recorded"}


@app.get("/api/session-ledger/{session_id}", response_model=SessionLedgerResponse)
def session_ledger(session_id: str) -> SessionLedgerResponse:
    """Rebuild a session's ledger from `intervention_events` + `decisions`.

    Lets the panel survive a reload or a fresh tab, which sessionStorage alone
    cannot. Returns an empty ledger rather than 404 for an unknown session — a
    session that has made no decisions yet is a legitimate, uninteresting state,
    not an error.
    """
    return ledger.build_session_ledger(db.get_db(), session_id)


@app.get("/api/product-availability/{product_id}", response_model=ProductAvailability)
def product_availability(
    product_id: str, quantity_left: int = Query(0, ge=0)
) -> ProductAvailability:
    """On-hand units minus the ones currently held for hesitating shoppers.

    `quantity_left` comes from the caller because the catalog lives on the
    frontend (`src/data/products.ts`) — see `ProductAvailability`. Expired holds
    fall out of the count here, at read time, so nothing has to sweep them.
    """
    reserved = reservations.active_count(db.get_db(), product_id)
    return ProductAvailability(
        product_id=product_id,
        quantity_left=quantity_left,
        reserved=reserved,
        available=max(0, quantity_left - reserved),
    )


@app.post("/api/cart-add")
def cart_add(payload: CartAddRequest) -> dict:
    """The shopper committed — the cart is the claim now, so drop the hold."""
    released = reservations.release(db.get_db(), payload.session_id, payload.product_id)
    return {"status": "released", "released": released}


@app.post("/api/companion-chat", response_model=CompanionChatResponse)
def companion_chat_endpoint(payload: CompanionChatRequest) -> CompanionChatResponse:
    """Reactive companion Q&A — product- and review-grounded, context-stuffed.

    Shares the Groq free-tier budget with root-cause analysis, so it degrades
    the same way: a clean `rate_limited` status rather than a crash.
    """
    if not config.companion_llm_is_configured():
        hint = config.missing_key_hint()
        return CompanionChatResponse(
            status="not_configured",
            message=f"No key configured for chat; set {hint} (or the COMPANION_ variant) in .env.",
        )

    reply, meta = companion_chat.chat(
        payload.product_context, payload.messages, payload.comparison_products, payload.search_history
    )

    if reply is None:
        status = "rate_limited" if meta.get("rate_limited") else "error"
        return CompanionChatResponse(
            status=status,
            message=meta.get("error", "Chat request failed"),
        )

    return CompanionChatResponse(
        status="success",
        reply=reply,
        model_used=meta.get("model_used"),
        latency_ms=meta.get("latency_ms", 0.0),
    )


# ============================================================================
# Re-engagement email system
# ============================================================================

from .agents import reengagement as reengagement_agent  # noqa: E402
from . import email_service  # noqa: E402


class EmailCaptureRequest(BaseModel):
    """Capture the shopper's email for re-engagement."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    email: str


class TimelineEventPayload(BaseModel):
    """A single behavioral event from the frontend timeline tracker."""

    model_config = ConfigDict(extra="forbid")
    type: str
    timestamp: float
    data: Dict[str, Any] = Field(default_factory=dict)
    duration_seconds: Optional[float] = None
    page: Optional[str] = None


class TimelineSyncRequest(BaseModel):
    """Batch of timeline events sent by the frontend periodic sync."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    events: list[TimelineEventPayload]


class SessionEndRequest(BaseModel):
    """Fired when the frontend detects session end (tab close / idle)."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    events: list[TimelineEventPayload] = Field(default_factory=list)
    converted: bool = False


def _store_timeline_events(
    connection, session_id: str, events: list[TimelineEventPayload]
) -> int:
    """Persist timeline events to SQLite. Returns count inserted."""
    import time as _time

    db.touch_session(connection, session_id, _time.time())
    inserted = 0
    for event in events:
        connection.execute(
            """
            INSERT INTO session_timelines
                (session_id, event_type, event_data, timestamp, duration_seconds, page)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                event.type,
                json.dumps(event.data),
                event.timestamp,
                event.duration_seconds,
                event.page,
            ),
        )
        inserted += 1
    connection.commit()
    return inserted


def _load_timeline(connection, session_id: str) -> list[dict]:
    """Load all timeline events for a session, oldest first."""
    rows = connection.execute(
        """
        SELECT event_type, event_data, timestamp, duration_seconds, page
        FROM session_timelines
        WHERE session_id = ?
        ORDER BY timestamp ASC
        """,
        (session_id,),
    ).fetchall()
    return [
        {
            "type": row["event_type"],
            "data": json.loads(row["event_data"]),
            "timestamp": row["timestamp"],
            "duration_seconds": row["duration_seconds"],
            "page": row["page"],
        }
        for row in rows
    ]


def _build_product_catalog_from_timeline(events: list[dict]) -> dict:
    """Extract product IDs from timeline and build a catalog stub.

    The real product catalog lives on the frontend (src/data/products.ts).
    We reconstruct what we can from the event data the frontend sent us.
    """
    catalog: Dict[str, Any] = {}
    for event in events:
        data = event.get("data", {})
        product_id = data.get("productId") or data.get("product_id")
        if product_id and product_id not in catalog:
            catalog[product_id] = {
                "id": product_id,
                "name": data.get("productName", data.get("product_name", product_id)),
                "price": data.get("price"),
                "category": data.get("category"),
            }
    return catalog


@app.post("/api/capture-email")
def capture_email(payload: EmailCaptureRequest) -> dict:
    """Store the shopper's email so we can send re-engagement messages."""
    import time as _time

    connection = db.get_db()
    db.touch_session(connection, payload.session_id, _time.time())
    connection.execute(
        """
        INSERT INTO session_emails (session_id, email, captured_at)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET email = excluded.email
        """,
        (payload.session_id, payload.email, _time.time()),
    )
    connection.commit()
    return {"status": "captured", "session_id": payload.session_id}


@app.post("/api/sync-timeline")
def sync_timeline(payload: TimelineSyncRequest) -> dict:
    """Receive a batch of behavioral events from the frontend."""
    connection = db.get_db()
    count = _store_timeline_events(connection, payload.session_id, payload.events)
    return {"status": "synced", "events_stored": count}


@app.post("/api/session-end")
def session_end(payload: SessionEndRequest) -> dict:
    """Session ended — store final events and trigger re-engagement if abandoned."""
    connection = db.get_db()

    # Store any remaining events
    if payload.events:
        _store_timeline_events(connection, payload.session_id, payload.events)

    # If they converted, no re-engagement needed
    if payload.converted:
        return {"status": "converted", "reengagement": False}

    # Check if we have an email for this session
    row = connection.execute(
        "SELECT email FROM session_emails WHERE session_id = ?",
        (payload.session_id,),
    ).fetchone()

    if not row:
        return {"status": "no_email", "reengagement": False}

    email = row["email"]

    # Load the full timeline
    events = _load_timeline(connection, payload.session_id)
    if len(events) < 3:
        return {"status": "insufficient_data", "reengagement": False}

    # Build product catalog from events
    catalog = _build_product_catalog_from_timeline(events)

    # Check if Groq is configured
    if not config.groq_is_configured():
        return {"status": "llm_not_configured", "reengagement": False}

    # Run the re-engagement pipeline
    result = reengagement_agent.run_reengagement_pipeline(
        session_id=payload.session_id,
        timeline_events=events,
        user_email=email,
        product_catalog=catalog,
    )

    if result.get("status") != "generated":
        return {"status": "generation_failed", "error": result.get("error", "Unknown")}

    import time as _time

    # Store the generated email
    connection.execute(
        """
        INSERT INTO reengagement_emails
            (session_id, email_to, subject, body_html, analysis_summary,
             behavioral_signals, generated_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'generated')
        """,
        (
            payload.session_id,
            email,
            result["subject"],
            result["body_html"],
            result.get("analysis_summary", ""),
            result.get("behavioral_signals", ""),
            _time.time(),
        ),
    )
    connection.commit()

    # Try to send the email
    sent = email_service.send_email(email, result["subject"], result["body_html"])
    if sent:
        connection.execute(
            """
            UPDATE reengagement_emails
            SET status = 'sent', sent_at = ?
            WHERE session_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (_time.time(), payload.session_id),
        )
        connection.commit()

    return {
        "status": "success",
        "reengagement": True,
        "email_sent": sent,
        "subject": result["subject"],
        "analysis_summary": result.get("analysis_summary"),
    }


@app.post("/api/trigger-reengagement/{session_id}")
def trigger_reengagement(session_id: str) -> dict:
    """Manual trigger for demo — generate and optionally send re-engagement email."""
    connection = db.get_db()

    # Load timeline
    events = _load_timeline(connection, session_id)
    if not events:
        raise HTTPException(status_code=404, detail="No timeline data for this session")

    # Get email (optional for preview)
    row = connection.execute(
        "SELECT email FROM session_emails WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    email = row["email"] if row else "demo@example.com"

    # Build catalog from events
    catalog = _build_product_catalog_from_timeline(events)

    if not config.groq_is_configured():
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured")

    # Run pipeline
    result = reengagement_agent.run_reengagement_pipeline(
        session_id=session_id,
        timeline_events=events,
        user_email=email,
        product_catalog=catalog,
    )

    if result.get("status") != "generated":
        raise HTTPException(
            status_code=500,
            detail=f"Re-engagement generation failed: {result.get('error', 'Unknown')}",
        )

    import time as _time

    # Store the email
    connection.execute(
        """
        INSERT INTO reengagement_emails
            (session_id, email_to, subject, body_html, analysis_summary,
             behavioral_signals, generated_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'generated')
        """,
        (
            session_id,
            email,
            result["subject"],
            result["body_html"],
            result.get("analysis_summary", ""),
            result.get("behavioral_signals", ""),
            _time.time(),
        ),
    )
    connection.commit()

    # Attempt to send
    sent = email_service.send_email(email, result["subject"], result["body_html"])
    if sent and email != "demo@example.com":
        connection.execute(
            """
            UPDATE reengagement_emails SET status = 'sent', sent_at = ?
            WHERE session_id = ? ORDER BY id DESC LIMIT 1
            """,
            (_time.time(), session_id),
        )
        connection.commit()

    return {
        "status": "success",
        "subject": result["subject"],
        "body_html": result["body_html"],
        "analysis_summary": result.get("analysis_summary"),
        "behavioral_signals": result.get("behavioral_signals"),
        "email_sent": sent and email != "demo@example.com",
        "model_used": result.get("model_used"),
        "latency_ms": result.get("latency_ms"),
    }


@app.get("/api/reengagement-preview/{session_id}")
def reengagement_preview(session_id: str) -> dict:
    """Preview the most recent re-engagement email for a session."""
    connection = db.get_db()
    row = connection.execute(
        """
        SELECT subject, body_html, analysis_summary, behavioral_signals,
               email_to, status, generated_at, sent_at
        FROM reengagement_emails
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No re-engagement email found for this session")

    return {
        "session_id": session_id,
        "subject": row["subject"],
        "body_html": row["body_html"],
        "analysis_summary": row["analysis_summary"],
        "behavioral_signals": row["behavioral_signals"],
        "email_to": row["email_to"],
        "status": row["status"],
        "generated_at": row["generated_at"],
        "sent_at": row["sent_at"],
    }


@app.get("/api/reengagement-sessions")
def reengagement_sessions() -> dict:
    """List all sessions with timeline data for the dashboard."""
    connection = db.get_db()

    rows = connection.execute(
        """
        SELECT
            t.session_id,
            e.email,
            COUNT(t.id) AS event_count,
            MIN(t.timestamp) AS first_event,
            MAX(t.timestamp) AS last_event,
            r.status AS email_status,
            r.subject AS email_subject
        FROM session_timelines t
        LEFT JOIN session_emails e ON t.session_id = e.session_id
        LEFT JOIN (
            SELECT session_id, status, subject,
                   ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY id DESC) AS rn
            FROM reengagement_emails
        ) r ON t.session_id = r.session_id AND r.rn = 1
        GROUP BY t.session_id
        ORDER BY MAX(t.timestamp) DESC
        """
    ).fetchall()

    sessions = [
        {
            "session_id": row["session_id"],
            "email": row["email"],
            "event_count": row["event_count"],
            "first_event": row["first_event"],
            "last_event": row["last_event"],
            "email_status": row["email_status"],
            "email_subject": row["email_subject"],
        }
        for row in rows
    ]

    return {"sessions": sessions, "total": len(sessions)}


@app.post("/api/browsing-intent")
def handle_browsing_intent(payload: Dict[str, Any]) -> dict:
    """Analyze real-time browsing intent cues via dedicated BROWSING_AGENT_GROQ_API_KEY."""
    return browsing_intent.analyze_browsing_intent(payload)




