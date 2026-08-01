"""FastAPI inference service for cart-abandonment prediction."""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
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


@app.post("/api/predict-abandonment", response_model=PredictionResponse)
def predict_abandonment(payload: SessionFeatures) -> PredictionResponse:
    if MODEL is None or EXPLAINER is None:
        raise HTTPException(status_code=503, detail="ML artifacts are not loaded")

    try:
        values = payload.model_dump()
        raw_frame = pd.DataFrame(
            [[values[name] for name in RAW_FEATURE_NAMES]],
            columns=RAW_FEATURE_NAMES,
        )
        frame = engineer_features(raw_frame)

        probability = float(MODEL.predict_proba(frame)[0, 1])
        if CALIBRATOR is not None:
            probability = float(CALIBRATOR.predict([probability])[0])

        # Distance from a coin flip, i.e. how decisive the model is here.
        confidence = abs(probability - 0.5) * 2.0
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

        return PredictionResponse(
            abandonment_probability=round(probability, 6),
            confidence_score=round(confidence, 6),
            risk_tier=_risk_tier(probability),
            top_contributing_features=top_features,
            feature_impacts=feature_impacts,
            status="success",
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Inference failed: {error}") from error
