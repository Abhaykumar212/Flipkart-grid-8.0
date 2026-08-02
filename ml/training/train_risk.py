from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import GroupKFold, RandomizedSearchCV
from xgboost import XGBClassifier

from backend.feature_engine.schema import RISK_MODEL_FEATURES, write_feature_schema
from ml.training.evaluate import binary_metrics, operating_table, reliability_curve


@dataclass
class ProbabilityCalibrator:
    kind: str
    estimator: object

    def transform(self, probability: np.ndarray) -> np.ndarray:
        probability = np.asarray(probability, dtype=float)
        if self.kind == "isotonic":
            return np.asarray(self.estimator.predict(probability), dtype=float)
        logits = np.log(np.clip(probability, 1e-7, 1 - 1e-7) / np.clip(1 - probability, 1e-7, 1))
        return np.asarray(self.estimator.predict_proba(logits.reshape(-1, 1))[:, 1], dtype=float)


def _choose_calibrator(y_fit: np.ndarray, p_fit: np.ndarray, y_eval: np.ndarray, p_eval: np.ndarray) -> tuple[ProbabilityCalibrator | None, dict[str, float]]:
    isotonic = ProbabilityCalibrator("isotonic", IsotonicRegression(out_of_bounds="clip").fit(p_fit, y_fit))
    logits = np.log(np.clip(p_fit, 1e-7, 1 - 1e-7) / np.clip(1 - p_fit, 1e-7, 1))
    sigmoid = ProbabilityCalibrator("sigmoid", LogisticRegression().fit(logits.reshape(-1, 1), y_fit))
    options = {"none": p_eval, "isotonic": isotonic.transform(p_eval), "sigmoid": sigmoid.transform(p_eval)}
    losses = {name: float(log_loss(y_eval, np.clip(values, 1e-7, 1 - 1e-7))) for name, values in options.items()}
    chosen = min(losses, key=losses.get)
    return ({"isotonic": isotonic, "sigmoid": sigmoid}.get(chosen), losses)


def main() -> None:
    data_path = Path("ml/data/decision_points.parquet")
    artifact = Path("ml/artifacts/risk/v1")
    artifact.mkdir(parents=True, exist_ok=True)
    frame = pd.read_parquet(data_path)
    if any(name.startswith("i_") for name in RISK_MODEL_FEATURES):
        raise AssertionError("post-treatment intervention features must not enter the risk model")
    missing = set(RISK_MODEL_FEATURES) - set(frame.columns)
    if missing:
        raise AssertionError(f"missing frozen features: {sorted(missing)}")
    train, val, test = (frame[frame["split"] == name].copy() for name in ("train", "val", "test"))
    x_train, y_train = train.loc[:, RISK_MODEL_FEATURES], train["y_abandoned"].to_numpy()
    x_val, y_val = val.loc[:, RISK_MODEL_FEATURES], val["y_abandoned"].to_numpy()
    x_test, y_test = test.loc[:, RISK_MODEL_FEATURES], test["y_abandoned"].to_numpy()

    baseline_lr = LogisticRegression(max_iter=1000, class_weight="balanced", n_jobs=-1).fit(x_train, y_train)
    baseline_rf = RandomForestClassifier(n_estimators=250, min_samples_leaf=4, class_weight="balanced", random_state=42, n_jobs=-1).fit(x_train, y_train)
    baselines = {
        "logistic_regression": binary_metrics(y_test, baseline_lr.predict_proba(x_test)[:, 1]),
        "random_forest": binary_metrics(y_test, baseline_rf.predict_proba(x_test)[:, 1]),
    }

    constraints = tuple(1 if name == "pay_failure_count" else -1 if name == "pay_checkout_max_step" else 0 for name in RISK_MODEL_FEATURES)
    base = XGBClassifier(n_estimators=350, objective="binary:logistic", eval_metric="logloss", random_state=42, n_jobs=1, tree_method="hist", monotone_constraints=constraints)
    search = RandomizedSearchCV(
        base,
        param_distributions={"max_depth": [3, 4, 5, 6], "learning_rate": [0.025, 0.04, 0.06, 0.08], "min_child_weight": [2, 4, 8], "subsample": [0.75, 0.9, 1.0], "colsample_bytree": [0.7, 0.85, 1.0], "reg_lambda": [1.0, 3.0, 6.0]},
        n_iter=24,
        scoring="neg_log_loss",
        cv=GroupKFold(3),
        random_state=42,
        n_jobs=2,
        verbose=1,
    )
    search.fit(x_train, y_train, groups=train["user_id"])
    params = dict(search.best_params_)
    model = XGBClassifier(n_estimators=2500, objective="binary:logistic", eval_metric="logloss", early_stopping_rounds=100, random_state=42, n_jobs=-1, tree_method="hist", monotone_constraints=constraints, **params)
    model.fit(x_train, y_train, eval_set=[(x_val, y_val)], verbose=False)

    users = val["user_id"].drop_duplicates().sort_values().to_numpy()
    fit_users = set(users[::2])
    cal_fit = val["user_id"].isin(fit_users).to_numpy()
    raw_val = model.predict_proba(x_val)[:, 1]
    calibrator, calibration_losses = _choose_calibrator(y_val[cal_fit], raw_val[cal_fit], y_val[~cal_fit], raw_val[~cal_fit])
    raw_test = model.predict_proba(x_test)[:, 1]
    probability = raw_test if calibrator is None else calibrator.transform(raw_test)
    metrics = binary_metrics(y_test, probability)
    metrics.update({
        "model_name": "risk",
        "model_version": "risk-v1",
        "training_data_version": "simulator-v1",
        "selected_calibration": "none" if calibrator is None else calibrator.kind,
        "calibration_validation_log_loss": calibration_losses,
        "best_params": params,
        "best_cv_neg_log_loss": float(search.best_score_),
        "baselines": baselines,
        "operating_table": operating_table(y_test, probability),
        "reliability_curve": reliability_curve(y_test, probability),
    })
    joblib.dump(model, artifact / "model.joblib")
    joblib.dump(calibrator, artifact / "calibrator.joblib")
    joblib.dump(shap.TreeExplainer(model), artifact / "explainer.joblib")
    write_feature_schema(artifact / "feature_schema.json")
    (artifact / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
