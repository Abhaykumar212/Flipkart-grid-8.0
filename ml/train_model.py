"""Train the Phase 1 XGBoost model and persist its SHAP explainer."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from xgboost import XGBClassifier

try:
    from .generate_dataset import DATA_PATH, FEATURE_NAMES
    from .feature_engineering import ALL_FEATURE_NAMES, engineer_features
except ImportError:  # Supports direct execution: python ml/train_model.py
    from generate_dataset import DATA_PATH, FEATURE_NAMES
    from feature_engineering import ALL_FEATURE_NAMES, engineer_features

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

    # Apply feature engineering: 14 raw → 30 features (14 raw + 16 engineered)
    X_raw = dataset[FEATURE_NAMES].astype(float)
    X = engineer_features(X_raw)
    y = dataset["is_abandoned"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    # Compute scale_pos_weight for class imbalance (65% abandoned vs 35% converted)
    neg_count = int((y_train == 0).sum())
    pos_count = int((y_train == 1).sum())
    scale_weight = neg_count / max(pos_count, 1)

    # -------------------------------------------------------------------
    # Use 5-fold CV with early stopping to find best n_estimators, then
    # retrain on full training set with that count.
    # -------------------------------------------------------------------
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # Find optimal iteration count via one fold
    fold_train_idx, fold_val_idx = next(cv.split(X_train, y_train))
    X_fold_train = X_train.iloc[fold_train_idx]
    y_fold_train = y_train.iloc[fold_train_idx]
    X_fold_val = X_train.iloc[fold_val_idx]
    y_fold_val = y_train.iloc[fold_val_idx]

    probe_model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=5000,
        learning_rate=0.015,
        max_depth=5,
        min_child_weight=2.0,
        subsample=0.80,
        colsample_bytree=0.70,
        colsample_bylevel=0.70,
        gamma=0.01,
        reg_alpha=0.03,
        reg_lambda=1.0,
        scale_pos_weight=scale_weight,
        max_delta_step=1,
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
        early_stopping_rounds=100,
    )
    probe_model.fit(
        X_fold_train,
        y_fold_train,
        eval_set=[(X_fold_val, y_fold_val)],
        verbose=False,
    )
    best_n = int(probe_model.best_iteration) + 1
    print(f"Early stopping found best iteration: {best_n}")

    # Retrain final model on ALL training data with the found iteration count
    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=best_n,
        learning_rate=0.015,
        max_depth=5,
        min_child_weight=2.0,
        subsample=0.80,
        colsample_bytree=0.70,
        colsample_bylevel=0.70,
        gamma=0.01,
        reg_alpha=0.03,
        reg_lambda=1.0,
        scale_pos_weight=scale_weight,
        max_delta_step=1,
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )
    model.fit(X_train, y_train)

    # Also compute CV probabilities for robust metric estimation
    cv_model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=best_n,
        learning_rate=0.015,
        max_depth=5,
        min_child_weight=2.0,
        subsample=0.80,
        colsample_bytree=0.70,
        colsample_bylevel=0.70,
        gamma=0.01,
        reg_alpha=0.03,
        reg_lambda=1.0,
        scale_pos_weight=scale_weight,
        max_delta_step=1,
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )
    cv_probs = cross_val_predict(
        cv_model, X_train, y_train, cv=cv, method="predict_proba"
    )[:, 1]
    cv_roc_auc = float(roc_auc_score(y_train, cv_probs))
    print(f"5-fold CV ROC-AUC on training set: {cv_roc_auc:.4f}")

    # Evaluate on holdout test set
    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    metrics = {
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "f1_score": float(f1_score(y_test, predictions)),
        "log_loss": float(log_loss(y_test, probabilities)),
        "cv_roc_auc": cv_roc_auc,
        "best_iteration": best_n,
        "train_rows": float(len(X_train)),
        "test_rows": float(len(X_test)),
        "positive_rate": float(y.mean()),
        "feature_count": len(ALL_FEATURE_NAMES),
    }

    # TreeExplainer returns additive log-odds attributions for this binary tree
    # model. The explainer itself is persisted so inference does no fitting.
    explainer = shap.TreeExplainer(model)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(explainer, EXPLAINER_PATH)
    FEATURE_NAMES_PATH.write_text(
        json.dumps(ALL_FEATURE_NAMES, indent=2), encoding="utf-8"
    )
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    importance_order = np.argsort(model.feature_importances_)[::-1][:10]
    print(f"\nPhase 1 XGBoost validation (with engineered features)")
    print("=" * 55)
    print(f"ROC-AUC       : {metrics['roc_auc']:.4f}")
    print(f"PR-AUC        : {metrics['pr_auc']:.4f}")
    print(f"Accuracy      : {metrics['accuracy']:.4f}")
    print(f"F1 Score      : {metrics['f1_score']:.4f}")
    print(f"Log Loss      : {metrics['log_loss']:.4f}")
    print(f"CV ROC-AUC    : {metrics['cv_roc_auc']:.4f}")
    print(f"Best Iteration: {metrics['best_iteration']}")
    print(f"Features      : {metrics['feature_count']} (14 raw + 16 engineered)")
    print("\nTop 10 XGBoost feature importances:")
    for rank, index in enumerate(importance_order, start=1):
        print(
            f"{rank}. {ALL_FEATURE_NAMES[index]}: "
            f"{float(model.feature_importances_[index]):.6f}"
        )
    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved SHAP explainer to {EXPLAINER_PATH}")
    return metrics


if __name__ == "__main__":
    train_model()
