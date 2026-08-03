# Risk model v1

This XGBoost binary classifier estimates abandonment probability at a decision point from the frozen 62-feature pre-intervention schema. Training uses simulator-v1 data, user-grouped cross-validation, held-out users, monotonic constraints on payment failures and checkout progress, and held-out probability calibration. Logistic-regression and random-forest baselines are reported alongside the deployed model.

The runtime refuses schema drift and degrades to `ABSTAIN` when its registry row or artifacts are unavailable. It is intended for intervention gating, not decisions about creditworthiness or user eligibility.

SHAP values explain the XGBoost model's uncalibrated raw log-odds. Calibration changes the displayed probability but is not represented by the SHAP decomposition, so factors must be read as directional model evidence rather than an additive explanation of the calibrated probability.

## Full-scale holdout results

| Metric | Result | Required |
|---|---:|---:|
| ROC-AUC | 0.7938 | >= 0.78 |
| PR-AUC | 0.9254 | >= 0.80 |
| ECE (15 bins) | 0.0113 | <= 0.03 |
| Brier score | 0.1468 | <= 0.18 |

These are synthetic holdout results from seed 42, not production claims. The
tracked metrics artifact also includes both baselines, the operating table,
reliability bins, and training-feature distributions used for report-only PSI.
