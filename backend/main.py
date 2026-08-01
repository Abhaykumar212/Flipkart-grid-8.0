"""FastAPI inference service for Phase 1 cart-abandonment prediction."""

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
EXPLAINER_PATH = ARTIFACT_DIR / "explainer.joblib"
FEATURE_NAMES_PATH = ARTIFACT_DIR / "feature_names.json"

# Add project root to path so we can import ml package
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.feature_engineering import (  # noqa: E402
    ALL_FEATURE_NAMES,
    RAW_FEATURE_NAMES,
    engineer_features,
)

MODEL: Any = None
EXPLAINER: Any = None
FEATURE_NAMES: list[str] = []


class SessionFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cart_dwell_time_seconds: float = Field(ge=10.0, le=600.0)
    cart_pdp_bounce_count: int = Field(ge=0, le=10)
    reviews_expanded_count: int = Field(ge=0, le=8)
    idle_time_before_checkout: float = Field(ge=0.0, le=300.0)
    delivery_pincode_checked: int = Field(ge=0, le=5)
    cart_value_to_aov_ratio: float = Field(ge=0.2, le=4.0)
    delivery_fee_percentage: float = Field(ge=0.0, le=15.0)
    est_delivery_days: int = Field(ge=1, le=10)
    has_price_dropped_recently: int = Field(ge=0, le=1)
    hist_abandonment_rate: float = Field(ge=0.0, le=1.0)
    discount_sensitivity_score: float = Field(ge=0.0, le=1.0)
    past_return_rate: float = Field(ge=0.0, le=0.5)
    wishlist_item_count: int = Field(ge=0, le=5)
    payment_method_saved: int = Field(ge=0, le=1)


class FeatureContribution(BaseModel):
    feature: str
    shap_value: float


class PredictionResponse(BaseModel):
    abandonment_probability: float
    confidence_score: float
    top_contributing_features: list[FeatureContribution]
    feature_impacts: dict[str, float]
    status: Literal["success"] = "success"


def _load_artifacts() -> None:
    global MODEL, EXPLAINER, FEATURE_NAMES

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
    FEATURE_NAMES = json.loads(FEATURE_NAMES_PATH.read_text(encoding="utf-8"))
    if len(FEATURE_NAMES) != len(ALL_FEATURE_NAMES):
        raise RuntimeError(
            f"feature_names.json must contain exactly {len(ALL_FEATURE_NAMES)} features, "
            f"got {len(FEATURE_NAMES)}"
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    _load_artifacts()
    yield


app = FastAPI(
    title="Flipkart GRiD 8.0 Phase 1 Prediction API",
    description="Real-time XGBoost cart-abandonment probability with SHAP attribution.",
    version="1.0.0",
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
def health() -> dict[str, str | int]:
    return {
        "status": "online",
        "model": "XGBoost",
        "explainer": "SHAP TreeExplainer",
        "feature_count": len(FEATURE_NAMES),
    }


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
        # Build raw 14-feature frame from input
        raw_frame = pd.DataFrame(
            [[values[name] for name in RAW_FEATURE_NAMES]],
            columns=RAW_FEATURE_NAMES,
        )
        # Apply feature engineering: 14 raw → 22 features
        frame = engineer_features(raw_frame)

        probability = float(MODEL.predict_proba(frame)[0, 1])
        confidence = abs(probability - 0.5) * 2.0
        shap_values = _extract_shap_values(frame)

        feature_impacts = {
            name: round(float(impact), 6)
            for name, impact in zip(FEATURE_NAMES, shap_values, strict=True)
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
            top_contributing_features=top_features,
            feature_impacts=feature_impacts,
            status="success",
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Inference failed: {error}") from error
