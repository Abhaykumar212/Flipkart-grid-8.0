from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import f1_score, hamming_loss, precision_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from xgboost import XGBClassifier

from backend.domain.causes import RootCause
from backend.feature_engine.schema import RISK_MODEL_FEATURES, write_feature_schema
from ml.training.model_types import ScaledOneVsRest

CAUSES = tuple(cause.value for cause in RootCause if cause is not RootCause.UNKNOWN)
UNKNOWN_THRESHOLD = 0.45


def _matrix(frame: pd.DataFrame) -> np.ndarray:
    rows = [tuple(value) for value in frame["y_causes"]]
    return MultiLabelBinarizer(classes=CAUSES).fit_transform(rows)


def _tune(y: np.ndarray, probability: np.ndarray) -> list[float]:
    thresholds = []
    for index in range(y.shape[1]):
        candidates = np.arange(0.30, 0.951, 0.025)
        scored = []
        for threshold in candidates:
            predicted = probability[:, index] >= threshold
            precision = precision_score(y[:, index], predicted, zero_division=0)
            score = f1_score(y[:, index], predicted, zero_division=0)
            scored.append((score if precision >= 0.57 else -1.0, score, threshold))
        eligible = max(scored, key=lambda item: (item[0], item[1]))
        thresholds.append(float(eligible[2]))
    return thresholds


def _metrics(
    y: np.ndarray,
    probability: np.ndarray,
    thresholds: np.ndarray,
    *,
    unknown_threshold: float = UNKNOWN_THRESHOLD,
) -> dict[str, object]:
    predicted = probability >= thresholds
    top2 = np.argsort(probability, axis=1)[:, -2:]
    top2_hits = [bool(y[row, top2[row]].any()) for row in range(len(y)) if y[row].any()]
    unknown = probability.max(axis=1) < unknown_threshold
    abandoning = y.any(axis=1)
    return {
        "micro_f1": float(f1_score(y, predicted, average="micro", zero_division=0)),
        "macro_f1": float(f1_score(y, predicted, average="macro", zero_division=0)),
        "hamming_loss": float(hamming_loss(y, predicted)),
        "top2_recall": float(np.mean(top2_hits)),
        "unknown_coverage": float(unknown.mean()),
        "mean_causes_abandoning": float(predicted[abandoning].sum(axis=1).mean()),
        "per_cause_precision": {CAUSES[i]: float(precision_score(y[:, i], predicted[:, i], zero_division=0)) for i in range(len(CAUSES))},
    }


def evaluate_saved_model() -> dict[str, object]:
    artifact = Path("ml/artifacts/root_cause/v1")
    frame = pd.read_parquet("ml/data/decision_points.parquet")
    test = frame[frame["split"] == "test"]
    model = joblib.load(artifact / "model.joblib")
    settings = json.loads((artifact / "thresholds.json").read_text(encoding="utf-8"))
    thresholds = np.asarray(settings["thresholds"])
    return _metrics(
        _matrix(test),
        model.predict_proba(test.loc[:, RISK_MODEL_FEATURES]),
        thresholds,
        unknown_threshold=float(settings["unknown_threshold"]),
    )


def main() -> None:
    artifact = Path("ml/artifacts/root_cause/v1")
    artifact.mkdir(parents=True, exist_ok=True)
    frame = pd.read_parquet("ml/data/decision_points.parquet")
    train, val, test = (frame[frame["split"] == name] for name in ("train", "val", "test"))
    y_train, y_val, y_test = _matrix(train), _matrix(val), _matrix(test)
    estimator = XGBClassifier(n_estimators=350, max_depth=4, learning_rate=0.05, min_child_weight=4, subsample=0.9, colsample_bytree=0.85, objective="binary:logistic", eval_metric="logloss", random_state=42, n_jobs=-1, tree_method="hist")
    x_train = train.loc[:, RISK_MODEL_FEATURES].copy()
    quality_index = CAUSES.index("PRODUCT_QUALITY_UNCERTAINTY")
    compressed = x_train.loc[y_train[:, quality_index] == 1].copy()
    for name in ("s_review_dwell_seconds", "s_duration_seconds", "c_age_seconds", "s_idle_seconds_current"):
        compressed[name] = 0.0
    augmented_x = pd.concat((x_train, compressed), ignore_index=True)
    augmented_y = np.concatenate((y_train, y_train[y_train[:, quality_index] == 1]), axis=0)
    classifier = OneVsRestClassifier(estimator, n_jobs=1).fit(x_train, y_train)
    quality_model = XGBClassifier(**estimator.get_params()).fit(augmented_x, augmented_y[:, quality_index])
    classifier.estimators_[quality_index] = quality_model
    raw_val = classifier.predict_proba(val.loc[:, RISK_MODEL_FEATURES])
    confidence_quantile = float(np.quantile(raw_val.max(axis=1), 0.08))
    class_scales = np.full(len(CAUSES), 1.3)
    class_scales[CAUSES.index("CHECKOUT_OR_PAYMENT_FAILURE")] = 1.5
    class_scales[CAUSES.index("PRODUCT_AVAILABILITY_CONCERN")] = 1.0
    class_scales[CAUSES.index("TRUST_OR_RETURN_POLICY_CONCERN")] = 1.0
    model = ScaledOneVsRest(classifier, confidence_quantile, class_scales)
    val_probability = model.predict_proba(val.loc[:, RISK_MODEL_FEATURES])
    thresholds = np.asarray(_tune(y_val, val_probability))
    trust_index = CAUSES.index("TRUST_OR_RETURN_POLICY_CONCERN")
    thresholds[trust_index] = min(0.95, thresholds[trust_index] + 0.05)
    availability_index = CAUSES.index("PRODUCT_AVAILABILITY_CONCERN")
    thresholds[[index for index in range(len(CAUSES)) if index not in (trust_index, availability_index)]] = 0.30
    test_probability = model.predict_proba(test.loc[:, RISK_MODEL_FEATURES])
    metrics = _metrics(
        y_test,
        test_probability,
        thresholds,
        unknown_threshold=UNKNOWN_THRESHOLD,
    )
    metrics.update({"model_name": "root_cause", "model_version": "root_cause-v1", "training_data_version": "simulator-v1"})
    joblib.dump(model, artifact / "model.joblib")
    joblib.dump([shap.TreeExplainer(estimator) for estimator in model.estimators_], artifact / "explainers.joblib")
    write_feature_schema(artifact / "feature_schema.json")
    (artifact / "thresholds.json").write_text(json.dumps({"causes": CAUSES, "thresholds": thresholds.tolist(), "unknown_threshold": UNKNOWN_THRESHOLD}, indent=2) + "\n", encoding="utf-8")
    (artifact / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
