# Root-cause model v1

Ten one-vs-rest XGBoost classifiers estimate the simulator's concrete abandonment causes from the same frozen, pre-intervention feature matrix as the risk model. Per-cause F1 thresholds are tuned on held-out users with a floor of 0.30. `UNKNOWN` is derived when every cause probability is below 0.35.

Evidence is selected from positive per-class SHAP values above 0.02 and then restricted to the cause's closed evidence family. The output is behavioral evidence, not a claim about a person's intent, and model failure degrades to `UNKNOWN`.
