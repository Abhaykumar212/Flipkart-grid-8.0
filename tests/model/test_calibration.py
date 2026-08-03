import json
from pathlib import Path


def test_calibration_report_meets_targets_and_has_ordered_bins() -> None:
    metrics = json.loads(
        Path("ml/artifacts/risk/v1/metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["ece_15"] <= 0.03
    assert metrics["brier"] <= 0.18
    curve = metrics["reliability_curve"]
    predictions = [row["mean_prediction"] for row in curve]
    assert predictions == sorted(predictions)
    assert sum(row["count"] for row in curve) > 10_000
