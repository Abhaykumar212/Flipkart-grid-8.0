from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import pandas as pd
import pytest

from backend.feature_engine.schema import RISK_MODEL_FEATURES, feature_schema_document
from backend.risk_model import loader
from backend.risk_model.predict import predict


ARTIFACT = Path("ml/artifacts/risk/v1")


def _metrics() -> dict[str, object]:
    return json.loads((ARTIFACT / "metrics.json").read_text(encoding="utf-8"))


def _require_runtime_artifacts() -> None:
    required = ("model.joblib", "calibrator.joblib", "explainer.joblib")
    if any(not (ARTIFACT / name).exists() for name in required):
        pytest.skip("ignored runtime artifacts are not present; run scripts/train_all.ps1")


def test_holdout_targets_and_baselines_are_reported() -> None:
    metrics = _metrics()
    assert metrics["roc_auc"] >= 0.78
    assert metrics["pr_auc"] >= 0.80
    assert metrics["ece_15"] <= 0.03
    assert metrics["brier"] <= 0.18
    assert set(metrics["baselines"]) == {"logistic_regression", "random_forest"}


def test_artifact_schema_is_exact_and_monotonic_constraints_hold() -> None:
    _require_runtime_artifacts()
    actual_schema = json.loads((ARTIFACT / "feature_schema.json").read_text(encoding="utf-8"))
    assert actual_schema == feature_schema_document()
    model = joblib.load(ARTIFACT / "model.joblib")
    frame = pd.read_parquet("ml/data/decision_points.parquet", columns=list(RISK_MODEL_FEATURES))
    baseline = frame.median(numeric_only=True).to_frame().T.loc[:, RISK_MODEL_FEATURES]

    no_failures = baseline.copy()
    many_failures = baseline.copy()
    no_failures["pay_failure_count"] = 0
    many_failures["pay_failure_count"] = 5
    assert model.predict_proba(many_failures)[0, 1] >= model.predict_proba(no_failures)[0, 1]

    checkout_start = baseline.copy()
    checkout_complete = baseline.copy()
    checkout_start["pay_checkout_max_step"] = 0
    checkout_complete["pay_checkout_max_step"] = 3
    assert model.predict_proba(checkout_complete)[0, 1] <= model.predict_proba(checkout_start)[0, 1]


def test_inference_with_shap_stays_under_latency_budget() -> None:
    _require_runtime_artifacts()
    frame = pd.read_parquet("ml/data/decision_points.parquet", columns=list(RISK_MODEL_FEATURES)).head(25)
    loader.load(ARTIFACT, version="risk-v1")
    try:
        latencies = []
        for row in frame.to_dict(orient="records"):
            started = perf_counter()
            result = predict({name: float(row[name]) for name in RISK_MODEL_FEATURES})
            latencies.append((perf_counter() - started) * 1_000)
            assert 0 <= result.probability <= 1
        assert float(np.percentile(latencies, 95)) < 100
    finally:
        loader.unload()
