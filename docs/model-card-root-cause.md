# Root-cause model v1

Ten one-vs-rest XGBoost classifiers estimate the simulator's concrete abandonment causes from the same frozen, pre-intervention feature matrix as the risk model. Per-cause F1 thresholds are tuned on held-out users with a floor of 0.30. `UNKNOWN` is derived when no evidence-grounded cause reaches 0.45. At most the three strongest fired labels are explained, bounding SHAP latency while retaining multi-label output.

Evidence is selected from positive per-class SHAP values above 0.02 and then restricted to the cause's closed evidence family. The output is behavioral evidence, not a claim about a person's intent, and model failure degrades to `UNKNOWN`.

## Full-scale holdout results

| Metric | Result | Required |
|---|---:|---:|
| Micro-F1 | 0.7850 | >= 0.70 |
| Macro-F1 | 0.7198 | >= 0.62 |
| Hamming loss | 0.0546 | <= 0.12 |
| Top-2 recall | 0.9771 | >= 0.80 |
| `UNKNOWN` coverage | 7.55% | 5-15% |
| Mean causes on abandoning sessions | 1.332 | >= 1.30 |

The smallest per-cause precision is 0.50 for the rare
`TRUST_OR_RETURN_POLICY_CONCERN` class; this is retained as a known synthetic-data
limitation rather than hidden by post-hoc holdout tuning. Discount policy and
recommendation confidence gates remain independent safeguards.
