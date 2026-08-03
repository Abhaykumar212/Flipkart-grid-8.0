"""FastAPI inference service for cart-abandonment prediction."""

from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Literal, Tuple

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

from . import config  # noqa: E402
from .agents import gate, root_cause  # noqa: E402
from .schemas import (  # noqa: E402
    CartContext,
    GateDecision,
    RootCauseResponse,
    TraceSpan,
)
from .trace import Stage, Status, TraceRecorder  # noqa: E402
from .products.router import router as products_router  # noqa: E402
from .event_ingestion.router import router as events_router  # noqa: E402
from .session_state.router import router as sessions_router  # noqa: E402
from .orchestrator.router import router as decisions_router  # noqa: E402
from .dashboard_api.router import router as dashboard_router  # noqa: E402
from .feedback.router import router as feedback_router  # noqa: E402
from .experimentation.router import router as experiments_router  # noqa: E402
from .demo.router import router as demo_router  # noqa: E402
from .observability.logging import configure_logging  # noqa: E402
from .observability.latency import metrics_registry  # noqa: E402
from .observability.drift import drift_monitor  # noqa: E402
from .dashboard_api.stream import broadcaster  # noqa: E402
from .risk_model import loader as risk_loader  # noqa: E402
from .root_cause import loader as root_cause_loader  # noqa: E402
from .storage.db import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402

LOGGER = logging.getLogger(__name__)

MODEL: Any = None
CALIBRATOR: Any = None
EXPLAINER: Any = None
FEATURE_NAMES: list = []
ARTIFACT_LOAD_ERROR: str | None = None


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
    # Stable per-browser-session id, used for dedup and budget accounting.
    session_id: str = "anonymous"
    # Manual "Re-run analysis" bypasses dedup/cooldown but not the session cap.
    force: bool = False


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
    global ARTIFACT_LOAD_ERROR
    configure_logging(config.LOG_LEVEL)
    try:
        _load_artifacts()
        ARTIFACT_LOAD_ERROR = None
    except Exception as error:
        ARTIFACT_LOAD_ERROR = str(error)
        LOGGER.warning("Legacy ML artifacts unavailable; inference endpoints will return 503: %s", error)
    try:
        risk_loader.load()
    except risk_loader.FeatureSchemaMismatch:
        raise
    except Exception as error:
        risk_loader.unload(str(error))
        LOGGER.warning("Risk model unavailable; decisions will abstain: %s", error)
    try:
        root_cause_loader.load()
    except root_cause_loader.FeatureSchemaMismatch:
        raise
    except Exception as error:
        root_cause_loader.unload(str(error))
        LOGGER.warning("Root-cause model unavailable; causes will be UNKNOWN: %s", error)
    yield


app = FastAPI(
    title="Flipkart GRiD 8.0 Cart-Abandonment Prediction API",
    description="Calibrated XGBoost abandonment probability with SHAP attribution.",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(config.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(products_router)
app.include_router(events_router)
app.include_router(sessions_router)
app.include_router(decisions_router)
app.include_router(dashboard_router)
app.include_router(feedback_router)
app.include_router(experiments_router)
app.include_router(demo_router)


@app.exception_handler(HTTPException)
async def http_problem_detail(_, error: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        media_type="application/problem+json",
        headers=error.headers,
        content={
            "type": "about:blank",
            "title": "Request failed",
            "status": error.status_code,
            "detail": error.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_problem_detail(_, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        media_type="application/problem+json",
        content=jsonable_encoder({
            "type": "about:blank",
            "title": "Validation error",
            "status": 422,
            "detail": "Request validation failed",
            "errors": error.errors(),
        }),
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


@app.get("/ready")
def ready() -> dict:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"database unavailable: {error}") from error
    if not risk_loader.is_ready():
        raise HTTPException(status_code=503, detail=risk_loader.load_error() or "risk model unavailable")
    if not root_cause_loader.is_ready():
        raise HTTPException(status_code=503, detail=root_cause_loader.load_error() or "root-cause model unavailable")
    return {"status": "ready", "risk_model": True, "root_cause_model": True}


@app.get("/metrics")
def metrics() -> dict:
    """Holdout evaluation of the deployed artifact, including the Bayes ceiling."""
    if not METRICS_PATH.exists():
        raise HTTPException(status_code=404, detail="metrics.json not found")
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


@app.get("/api/v1/metrics", tags=["observability"])
def runtime_metrics() -> dict:
    metrics_registry.gauge("sse_clients", broadcaster.subscriber_count)
    return {**metrics_registry.snapshot(), "drift": drift_monitor.snapshot()}


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
        "groq_configured": config.groq_is_configured(),
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

    def envelope(status: str, analysis=None, meta=None, message=None) -> RootCauseResponse:
        meta = meta or {}
        return RootCauseResponse(
            pipeline_run_id=recorder.run_id,
            status=status,
            prediction=prediction.model_dump(),
            gate=gate_model,
            analysis=analysis,
            model_used=meta.get("model_used"),
            latency_ms=meta.get("latency_ms", 0.0),
            message=message,
            trace=[TraceSpan(**span) for span in recorder.spans],
        )

    if not decision.fired:
        return envelope("gate_not_met", message=decision.reason)

    if not config.groq_is_configured():
        recorder.add(
            Stage.ROOT_CAUSE_AGENT,
            "Skipped — GROQ_API_KEY not configured",
            status=Status.SKIPPED,
            detail={"hint": "Set GROQ_API_KEY in .env (see .env.example)"},
        )
        return envelope(
            "not_configured",
            message="GROQ_API_KEY is not set; copy .env.example to .env and add a key.",
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
    return envelope("success", analysis=analysis, meta=meta)
