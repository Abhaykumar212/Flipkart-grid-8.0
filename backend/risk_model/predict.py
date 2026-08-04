from __future__ import annotations

from time import perf_counter

import numpy as np
import pandas as pd

from backend.domain.enums import RiskBand
from backend.feature_engine.schema import RISK_MODEL_FEATURES
from backend.risk_model.contracts import RiskFactor, RiskPrediction
from backend.risk_model import loader


def _band(probability: float) -> RiskBand:
    if probability >= 0.75:
        return RiskBand.HIGH
    if probability >= 0.45:
        return RiskBand.MEDIUM
    return RiskBand.LOW


def predict(features: dict[str, float]) -> RiskPrediction:
    started = perf_counter()
    try:
        loaded = loader.runtime()
    except loader.ArtifactUnavailable:
        return RiskPrediction(1.0, 0.0, RiskBand.HIGH, "risk-unavailable", (), (perf_counter() - started) * 1000)
    values = np.asarray([[float(features.get(name, 0.0)) for name in RISK_MODEL_FEATURES]], dtype=float)
    frame = pd.DataFrame(values, columns=RISK_MODEL_FEATURES)
    raw = float(loaded.model.predict_proba(frame)[0, 1])
    probability = raw if loaded.calibrator is None else float(loaded.calibrator.transform(np.asarray([raw]))[0])
    # The simulator and model are defined only for an actual cart. Keep the
    # Phase-5 no-cart contract conservative instead of extrapolating trees.
    if features.get("c_item_count", 0.0) <= 0 or features.get("s_cart_add_count", 0.0) <= 0:
        probability = min(probability, 0.12)
    explanation = loaded.explainer(frame)
    shap_values = np.asarray(explanation.values, dtype=float)
    if shap_values.ndim == 3:
        shap_values = shap_values[:, :, -1]
    row = shap_values[0]
    shap_by_feature = {name: float(row[index]) for index, name in enumerate(RISK_MODEL_FEATURES)}
    indices = np.argsort(np.abs(row))[::-1][:5]
    factors = tuple(RiskFactor(RISK_MODEL_FEATURES[index], float(values[0, index]), float(row[index])) for index in indices)
    confidence = min(1.0, abs(probability - 0.5) * 2)
    return RiskPrediction(
        float(np.clip(probability, 0, 1)),
        confidence,
        _band(probability),
        loaded.version,
        factors,
        (perf_counter() - started) * 1000,
        shap_by_feature=shap_by_feature,
    )
