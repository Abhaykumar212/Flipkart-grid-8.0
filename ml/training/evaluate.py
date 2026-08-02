from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from backend.feature_engine.schema import RISK_MODEL_FEATURES


def expected_calibration_error(y: np.ndarray, probability: np.ndarray, bins: int = 15) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    result = 0.0
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        selected = (probability >= lower) & (probability < upper if upper < 1 else probability <= upper)
        if selected.any():
            result += selected.mean() * abs(float(y[selected].mean()) - float(probability[selected].mean()))
    return float(result)


def reliability_curve(y: np.ndarray, probability: np.ndarray, bins: int = 15) -> list[dict[str, float | int]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    result = []
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        selected = (probability >= lower) & (probability < upper if upper < 1 else probability <= upper)
        if selected.any():
            result.append({"mean_prediction": float(probability[selected].mean()), "observed_rate": float(y[selected].mean()), "count": int(selected.sum())})
    return result


def binary_metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    probability = np.clip(probability, 1e-7, 1 - 1e-7)
    return {
        "roc_auc": float(roc_auc_score(y, probability)),
        "pr_auc": float(average_precision_score(y, probability)),
        "log_loss": float(log_loss(y, probability)),
        "brier": float(brier_score_loss(y, probability)),
        "ece_15": expected_calibration_error(y, probability),
    }


def operating_table(y: np.ndarray, probability: np.ndarray) -> list[dict[str, float]]:
    rows = []
    for threshold in np.arange(0.30, 0.91, 0.05):
        predicted = probability >= threshold
        tp = int((predicted & (y == 1)).sum())
        fp = int((predicted & (y == 0)).sum())
        fn = int((~predicted & (y == 1)).sum())
        rows.append({"threshold": round(float(threshold), 2), "precision": tp / max(tp + fp, 1), "recall": tp / max(tp + fn, 1), "intervention_rate": float(predicted.mean())})
    return rows


def _transform(calibrator: object | None, probability: np.ndarray) -> np.ndarray:
    return probability if calibrator is None else np.asarray(calibrator.transform(probability), dtype=float)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("risk", "root_cause"), required=True)
    args = parser.parse_args()
    if args.model != "risk":
        from ml.training.train_root_cause import evaluate_saved_model
        print(json.dumps(evaluate_saved_model(), indent=2))
        return
    artifact = Path("ml/artifacts/risk/v1")
    frame = pd.read_parquet("ml/data/decision_points.parquet")
    test = frame[frame["split"] == "test"]
    model = joblib.load(artifact / "model.joblib")
    calibrator = joblib.load(artifact / "calibrator.joblib")
    raw = model.predict_proba(test.loc[:, RISK_MODEL_FEATURES])[:, 1]
    probability = _transform(calibrator, raw)
    report = binary_metrics(test["y_abandoned"].to_numpy(), probability)
    report["operating_table"] = operating_table(test["y_abandoned"].to_numpy(), probability)
    report["reliability_curve"] = reliability_curve(test["y_abandoned"].to_numpy(), probability)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
