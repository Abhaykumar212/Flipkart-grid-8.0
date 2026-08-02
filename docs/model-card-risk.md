# Risk model v1

This XGBoost binary classifier estimates abandonment probability at a decision point from the frozen 62-feature pre-intervention schema. Training uses simulator-v1 data, user-grouped cross-validation, held-out users, monotonic constraints on payment failures and checkout progress, and held-out probability calibration. Logistic-regression and random-forest baselines are reported alongside the deployed model.

The runtime refuses schema drift and degrades to `ABSTAIN` when its registry row or artifacts are unavailable. It is intended for intervention gating, not decisions about creditworthiness or user eligibility.

SHAP values explain the XGBoost model's uncalibrated raw log-odds. Calibration changes the displayed probability but is not represented by the SHAP decomposition, so factors must be read as directional model evidence rather than an additive explanation of the calibrated probability.
