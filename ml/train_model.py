"""Train the Phase 1 XGBoost model and persist its SHAP explainer."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import accuracy_score, average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

try:
    from .generate_dataset import DATA_PATH, FEATURE_NAMES
except ImportError:  # Supports direct execution: python ml/train_model.py
    from generate_dataset import DATA_PATH, FEATURE_NAMES

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "model.joblib"
EXPLAINER_PATH = ARTIFACT_DIR / "explainer.joblib"
FEATURE_NAMES_PATH = ARTIFACT_DIR / "feature_names.json"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"


def train_model() -> dict[str, float]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATA_PATH}. Run 'python ml/generate_dataset.py' first."
        )

    dataset = pd.read_csv(DATA_PATH)
    expected_columns = [*FEATURE_NAMES, "is_abandoned"]
    if list(dataset.columns) != expected_columns:
        raise ValueError(
            "Dataset schema mismatch. Expected exact columns: "
            + ", ".join(expected_columns)
        )

    X = dataset[FEATURE_NAMES].astype(float)
    y = dataset["is_abandoned"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=450,
        learning_rate=0.035,
        max_depth=4,
        min_child_weight=4.0,
        subsample=0.85,
        colsample_bytree=0.85,
        gamma=0.05,
        reg_alpha=0.08,
        reg_lambda=1.4,
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )
    model.fit(X_train, y_train)

    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    metrics = {
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "train_rows": float(len(X_train)),
        "test_rows": float(len(X_test)),
        "positive_rate": float(y.mean()),
    }

    # TreeExplainer returns additive log-odds attributions for this binary tree
    # model. The explainer itself is persisted so inference does no fitting.
    explainer = shap.TreeExplainer(model)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(explainer, EXPLAINER_PATH)
    FEATURE_NAMES_PATH.write_text(json.dumps(FEATURE_NAMES, indent=2), encoding="utf-8")
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    importance_order = np.argsort(model.feature_importances_)[::-1][:5]
    print("\nPhase 1 XGBoost validation")
    print("=" * 42)
    print(f"ROC-AUC : {metrics['roc_auc']:.4f}")
    print(f"PR-AUC  : {metrics['pr_auc']:.4f}")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print("\nTop 5 standard XGBoost feature importances:")
    for rank, index in enumerate(importance_order, start=1):
        print(
            f"{rank}. {FEATURE_NAMES[index]}: "
            f"{float(model.feature_importances_[index]):.6f}"
        )
    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved SHAP explainer to {EXPLAINER_PATH}")
    return metrics


if __name__ == "__main__":
    train_model()
