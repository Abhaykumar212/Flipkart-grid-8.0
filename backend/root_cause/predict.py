from __future__ import annotations

from time import perf_counter

import numpy as np
import pandas as pd

from backend.domain.causes import RootCause
from backend.feature_engine.schema import RISK_MODEL_FEATURES
from backend.root_cause import loader
from backend.root_cause.contracts import CausePrediction, CauseResult
from backend.root_cause.evidence import evidence_for


def predict(features: dict[str, float]) -> CauseResult:
    started = perf_counter()
    try:
        loaded = loader.runtime()
    except loader.ArtifactUnavailable:
        return CauseResult.unknown(model_version="root_cause-unavailable", latency_ms=(perf_counter() - started) * 1000)
    frame = pd.DataFrame([[float(features.get(name, 0.0)) for name in RISK_MODEL_FEATURES]], columns=RISK_MODEL_FEATURES)
    probability = np.asarray(loaded.model.predict_proba(frame)[0], dtype=float)
    confidence = float(probability.max())
    if confidence < loaded.unknown_threshold:
        return CauseResult.unknown(confidence, model_version=loaded.version, latency_ms=(perf_counter() - started) * 1000)
    predictions = []
    fired = sorted(
        (
            (index, name)
            for index, (name, threshold) in enumerate(
                zip(loaded.causes, loaded.thresholds, strict=True)
            )
            if probability[index] >= threshold
        ),
        key=lambda item: (-probability[item[0]], item[1]),
    )[:3]
    for index, name in fired:
        values = np.asarray(
            loaded.explainers[index].shap_values(frame, check_additivity=False),
            dtype=float,
        )[0]
        shap_by_name = {feature: float(values[position]) for position, feature in enumerate(RISK_MODEL_FEATURES)}
        cause = RootCause(name)
        evidence = evidence_for(cause, shap_by_name)
        if evidence:
            predictions.append(CausePrediction(cause, float(probability[index]), evidence))
    if (
        not predictions
        or max(item.probability for item in predictions) < loaded.unknown_threshold
    ):
        return CauseResult.unknown(confidence, model_version=loaded.version, latency_ms=(perf_counter() - started) * 1000)
    predictions.sort(key=lambda item: (-item.probability, item.cause.value))
    return CauseResult(tuple(predictions), loaded.version, False, confidence, (perf_counter() - started) * 1000)
