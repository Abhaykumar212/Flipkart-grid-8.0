"""Train, calibrate and evaluate the cart-abandonment model.

What this script reports and why
--------------------------------
Raw ROC-AUC in isolation is close to meaningless on synthetic data — it is
bounded by however much signal the generator put there. So we report:

* **Bayes-optimal ceiling** — the best score achievable by *any* model given the
  observable features. Our distance from it is the real measure of model quality.
* **Calibration** (Brier, ECE, reliability) — Phase 2 fires interventions at
  probability thresholds, so a probability of 0.7 must actually mean 70%.
  A well-ranked but poorly-calibrated model would silently mis-target spend.
* **Bootstrap confidence intervals** — so a 0.002 difference between runs is not
  mistaken for a real improvement.
* **Decision thresholds** — precision/recall/coverage at each operating point,
  which is what the intervention layer actually needs to pick a trigger.

Note on class weighting
-----------------------
We deliberately do NOT use `scale_pos_weight`. It improves nothing here (the
68/32 split is mild) and it systematically inflates predicted probabilities away
from the true rate, which is exactly the property Phase 2 depends on. Class
balance is handled where it belongs: at the decision threshold, not in the loss.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

try:
    from .generate_dataset import (
        BAYES_PROBABILITY_NAME,
        DATA_PATH,
        FEATURE_NAMES,
        TARGET_NAME,
    )
    from .feature_engineering import ALL_FEATURE_NAMES, engineer_features
except ImportError:  # Supports direct execution: python ml/train_model.py
    from generate_dataset import (
        BAYES_PROBABILITY_NAME,
        DATA_PATH,
        FEATURE_NAMES,
        TARGET_NAME,
    )
    from feature_engineering import ALL_FEATURE_NAMES, engineer_features

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "model.joblib"
CALIBRATOR_PATH = ARTIFACT_DIR / "calibrator.joblib"
EXPLAINER_PATH = ARTIFACT_DIR / "explainer.joblib"
FEATURE_NAMES_PATH = ARTIFACT_DIR / "feature_names.json"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"

RANDOM_STATE = 42

XGB_PARAMS = dict(
    objective="binary:logistic",
    eval_metric="logloss",
    learning_rate=0.05,
    max_depth=6,
    min_child_weight=4.0,
    subsample=0.85,
    colsample_bytree=0.80,
    gamma=0.02,
    reg_alpha=0.05,
    reg_lambda=1.5,
    random_state=RANDOM_STATE,
    n_jobs=-1,
    tree_method="hist",
)


def expected_calibration_error(
    y_true: np.ndarray, y_prob: np.ndarray, bins: int = 15
) -> float:
    """Mean gap between predicted confidence and observed frequency, bin-weighted."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    index = np.clip(np.digitize(y_prob, edges[1:-1]), 0, bins - 1)
    total = 0.0
    for b in range(bins):
        mask = index == b
        if not mask.any():
            continue
        total += mask.mean() * abs(y_true[mask].mean() - y_prob[mask].mean())
    return float(total)


def bootstrap_auc_ci(
    y_true: np.ndarray, y_prob: np.ndarray, rounds: int = 200, seed: int = RANDOM_STATE
) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for ROC-AUC."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    scores = []
    for _ in range(rounds):
        idx = rng.integers(0, n, n)
        if y_true[idx].min() == y_true[idx].max():
            continue
        scores.append(roc_auc_score(y_true[idx], y_prob[idx]))
    return float(np.percentile(scores, 2.5)), float(np.percentile(scores, 97.5))


def threshold_table(y_true: np.ndarray, y_prob: np.ndarray) -> list[dict[str, float]]:
    """Operating points for the Phase 2 intervention trigger."""
    base_rate = float(y_true.mean())
    rows = []
    for threshold in (0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9):
        flagged = y_prob >= threshold
        coverage = float(flagged.mean())
        if flagged.sum() == 0:
            continue
        precision = float(precision_score(y_true, flagged, zero_division=0))
        rows.append(
            {
                "threshold": threshold,
                "coverage": round(coverage, 4),
                "precision": round(precision, 4),
                "recall": round(float(recall_score(y_true, flagged, zero_division=0)), 4),
                "f1": round(float(f1_score(y_true, flagged, zero_division=0)), 4),
                "lift_over_base_rate": round(precision / base_rate, 4),
            }
        )
    return rows


def train_model() -> dict:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATA_PATH}. Run 'python ml/generate_dataset.py' first."
        )

    dataset = pd.read_csv(DATA_PATH)
    expected = [*FEATURE_NAMES, TARGET_NAME, BAYES_PROBABILITY_NAME]
    if list(dataset.columns) != expected:
        raise ValueError(
            "Dataset schema mismatch. Expected exact columns: " + ", ".join(expected)
        )

    X = engineer_features(dataset[FEATURE_NAMES].astype(float))
    y = dataset[TARGET_NAME].astype(int).to_numpy()
    bayes_probability = dataset[BAYES_PROBABILITY_NAME].to_numpy()

    # Hard guard: the oracle column must never reach the model.
    leaked = set(X.columns) & {BAYES_PROBABILITY_NAME, TARGET_NAME}
    if leaked:
        raise AssertionError(f"Target/oracle leaked into features: {leaked}")

    # Three-way split: fit on train, early-stop + calibrate on calib, report on test.
    # Calibrating on the same data used for early stopping is fine (both are
    # out-of-sample w.r.t. the trees), but the test set stays untouched by both.
    X_train, X_hold, y_train, y_hold, _, bayes_hold = train_test_split(
        X, y, bayes_probability, test_size=0.40, random_state=RANDOM_STATE, stratify=y
    )
    X_calib, X_test, y_calib, y_test, _, bayes_test = train_test_split(
        X_hold, y_hold, bayes_hold, test_size=0.50, random_state=RANDOM_STATE, stratify=y_hold
    )

    model = XGBClassifier(**XGB_PARAMS, n_estimators=4000, early_stopping_rounds=100)
    model.fit(X_train, y_train, eval_set=[(X_calib, y_calib)], verbose=False)
    best_iteration = int(model.best_iteration) + 1
    print(f"Early stopping selected {best_iteration} trees.")

    # ------------------------------------------------------------------
    # Should we post-hoc calibrate at all?
    #
    # Isotonic regression is monotone (so AUC is unaffected) but it is fitted
    # from data, which costs variance. Because we dropped `scale_pos_weight`,
    # the model may already be well calibrated — in which case isotonic would
    # make things *worse*. We decide empirically, on a slice of the calibration
    # set the calibrator never sees. The test set plays no part in this choice.
    # ------------------------------------------------------------------
    X_cfit, X_ceval, y_cfit, y_ceval = train_test_split(
        X_calib, y_calib, test_size=0.5, random_state=RANDOM_STATE, stratify=y_calib
    )
    trial = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    trial.fit(model.predict_proba(X_cfit)[:, 1], y_cfit)

    raw_ceval = model.predict_proba(X_ceval)[:, 1]
    loss_raw = log_loss(y_ceval, raw_ceval)
    loss_isotonic = log_loss(y_ceval, trial.predict(raw_ceval))
    use_calibration = loss_isotonic < loss_raw
    print(
        f"Calibration check on held-out slice: raw log-loss {loss_raw:.4f} vs "
        f"isotonic {loss_isotonic:.4f} -> "
        f"{'using isotonic' if use_calibration else 'keeping raw probabilities'}"
    )

    if use_calibration:
        # Refit on the full calibration set now that we've decided to use it.
        calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        calibrator.fit(model.predict_proba(X_calib)[:, 1], y_calib)
    else:
        calibrator = None

    raw_test = model.predict_proba(X_test)[:, 1]
    cal_test = calibrator.predict(raw_test) if calibrator is not None else raw_test
    predictions = (cal_test >= 0.5).astype(int)

    ci_low, ci_high = bootstrap_auc_ci(y_test, cal_test)

    bayes = {
        "roc_auc": float(roc_auc_score(y_test, bayes_test)),
        "pr_auc": float(average_precision_score(y_test, bayes_test)),
        "log_loss": float(log_loss(y_test, bayes_test)),
        "brier": float(brier_score_loss(y_test, bayes_test)),
        "accuracy": float(accuracy_score(y_test, (bayes_test >= 0.5).astype(int))),
    }

    metrics = {
        "roc_auc": float(roc_auc_score(y_test, cal_test)),
        "roc_auc_ci95": [round(ci_low, 4), round(ci_high, 4)],
        "pr_auc": float(average_precision_score(y_test, cal_test)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "f1_score": float(f1_score(y_test, predictions)),
        "log_loss": float(log_loss(y_test, cal_test)),
        "brier_score": float(brier_score_loss(y_test, cal_test)),
        "expected_calibration_error": expected_calibration_error(y_test, cal_test),
        # Whether post-hoc calibration was applied, and the raw reference.
        "isotonic_calibration_applied": bool(use_calibration),
        "log_loss_uncalibrated": float(log_loss(y_test, raw_test)),
        "brier_uncalibrated": float(brier_score_loss(y_test, raw_test)),
        "ece_uncalibrated": expected_calibration_error(y_test, raw_test),
        # Theoretical ceiling and how close we got.
        "bayes_optimal": {k: round(v, 6) for k, v in bayes.items()},
        "auc_efficiency_vs_bayes": round(
            float(roc_auc_score(y_test, cal_test)) / bayes["roc_auc"], 4
        ),
        "logloss_excess_vs_bayes": round(
            float(log_loss(y_test, cal_test)) - bayes["log_loss"], 6
        ),
        "best_iteration": best_iteration,
        "train_rows": int(len(X_train)),
        "calibration_rows": int(len(X_calib)),
        "test_rows": int(len(X_test)),
        "positive_rate": float(y.mean()),
        "feature_count": len(ALL_FEATURE_NAMES),
        "decision_thresholds": threshold_table(y_test, cal_test),
    }

    explainer = shap.TreeExplainer(model)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    # Always written (possibly None) so the serving layer has one contract.
    joblib.dump(calibrator, CALIBRATOR_PATH)
    joblib.dump(explainer, EXPLAINER_PATH)
    FEATURE_NAMES_PATH.write_text(json.dumps(ALL_FEATURE_NAMES, indent=2), encoding="utf-8")
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # ---------------- Report ----------------
    print("\n" + "=" * 62)
    print("CART ABANDONMENT MODEL — HOLDOUT EVALUATION")
    print("=" * 62)
    print(f"{'':<26}{'model':>12}{'Bayes max':>12}{'gap':>10}")
    print("-" * 62)
    print(f"{'ROC-AUC':<26}{metrics['roc_auc']:>12.4f}{bayes['roc_auc']:>12.4f}"
          f"{bayes['roc_auc'] - metrics['roc_auc']:>10.4f}")
    print(f"{'PR-AUC':<26}{metrics['pr_auc']:>12.4f}{bayes['pr_auc']:>12.4f}"
          f"{bayes['pr_auc'] - metrics['pr_auc']:>10.4f}")
    print(f"{'Accuracy':<26}{metrics['accuracy']:>12.4f}{bayes['accuracy']:>12.4f}"
          f"{bayes['accuracy'] - metrics['accuracy']:>10.4f}")
    print(f"{'Log loss (lower better)':<26}{metrics['log_loss']:>12.4f}{bayes['log_loss']:>12.4f}"
          f"{metrics['log_loss'] - bayes['log_loss']:>10.4f}")
    print(f"{'Brier (lower better)':<26}{metrics['brier_score']:>12.4f}{bayes['brier']:>12.4f}"
          f"{metrics['brier_score'] - bayes['brier']:>10.4f}")
    print("-" * 62)
    print(f"ROC-AUC 95% CI            : [{ci_low:.4f}, {ci_high:.4f}]")
    print(f"Efficiency vs Bayes limit : {metrics['auc_efficiency_vs_bayes']:.2%}")
    if use_calibration:
        print("\nIsotonic calibration applied (it improved held-out log-loss):")
        print(f"  log loss {metrics['log_loss_uncalibrated']:.4f} -> {metrics['log_loss']:.4f}")
        print(f"  Brier    {metrics['brier_uncalibrated']:.4f} -> {metrics['brier_score']:.4f}")
        print(f"  ECE      {metrics['ece_uncalibrated']:.4f} -> {metrics['expected_calibration_error']:.4f}")
    else:
        print("\nNo post-hoc calibration applied — raw model probabilities were")
        print("already better calibrated than the isotonic fit on held-out data.")
        print(f"  ECE   : {metrics['expected_calibration_error']:.4f} (0 = perfect)")
        print(f"  Brier : {metrics['brier_score']:.4f} vs Bayes floor {bayes['brier']:.4f}")

    print("\nPhase 2 trigger operating points:")
    print(f"{'thresh':>7}{'coverage':>10}{'precision':>11}{'recall':>9}{'lift':>7}")
    for row in metrics["decision_thresholds"]:
        print(f"{row['threshold']:>7.2f}{row['coverage']:>10.1%}{row['precision']:>11.3f}"
              f"{row['recall']:>9.3f}{row['lift_over_base_rate']:>7.2f}x")

    order = np.argsort(model.feature_importances_)[::-1][:12]
    print("\nTop 12 features by gain:")
    for rank, index in enumerate(order, start=1):
        print(f"{rank:>3}. {ALL_FEATURE_NAMES[index]:<34}"
              f"{float(model.feature_importances_[index]):.4f}")

    print(f"\nSaved model      -> {MODEL_PATH}")
    print(f"Saved calibrator -> {CALIBRATOR_PATH}")
    print(f"Saved explainer  -> {EXPLAINER_PATH}")
    return metrics


if __name__ == "__main__":
    train_model()
