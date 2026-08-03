from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import pytest

from backend.feature_engine.schema import RISK_MODEL_FEATURES, feature_schema_document
from backend.root_cause import loader
from backend.root_cause.predict import predict


ARTIFACT = Path("ml/artifacts/root_cause/v1")


def test_multilabel_holdout_targets_are_met() -> None:
    metrics = json.loads((ARTIFACT / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["micro_f1"] >= 0.70
    assert metrics["macro_f1"] >= 0.62
    assert metrics["hamming_loss"] <= 0.12
    assert metrics["top2_recall"] >= 0.80
    assert 0.05 <= metrics["unknown_coverage"] <= 0.15
    assert metrics["mean_causes_abandoning"] >= 1.30
    assert min(metrics["per_cause_precision"].values()) >= 0.50


def test_artifact_schema_and_explanations_match_the_frozen_contract() -> None:
    if not (ARTIFACT / "model.joblib").exists():
        pytest.skip("ignored runtime artifacts are not present; run scripts/train_all.ps1")
    assert json.loads((ARTIFACT / "feature_schema.json").read_text(encoding="utf-8")) == feature_schema_document()
    frame = pd.read_parquet("ml/data/decision_points.parquet", columns=list(RISK_MODEL_FEATURES)).head(20)
    loader.load(ARTIFACT, version="root_cause-v1")
    try:
        latencies = []
        for row in frame.to_dict(orient="records"):
            started = perf_counter()
            result = predict({name: float(row[name]) for name in RISK_MODEL_FEATURES})
            latencies.append((perf_counter() - started) * 1_000)
            if not result.abstained:
                assert all(item.evidence_keys for item in result.root_causes)
        assert float(np.percentile(latencies, 95)) < 100
    finally:
        loader.unload()
