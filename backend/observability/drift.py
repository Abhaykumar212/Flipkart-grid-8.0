from __future__ import annotations

from collections import defaultdict, deque
import json
import logging
from pathlib import Path
from threading import RLock
from typing import Any

import numpy as np

from backend import config


LOGGER = logging.getLogger(__name__)
EPSILON = 1e-6


def population_stability_index(expected: list[float], actual: list[float]) -> float:
    """Calculate PSI from equally sized probability/count buckets."""

    if len(expected) != len(actual) or not expected:
        raise ValueError("expected and actual must be non-empty and equally sized")
    expected_array = np.asarray(expected, dtype=float)
    actual_array = np.asarray(actual, dtype=float)
    if expected_array.sum() <= 0 or actual_array.sum() <= 0:
        return 0.0
    expected_ratio = np.clip(expected_array / expected_array.sum(), EPSILON, None)
    actual_ratio = np.clip(actual_array / actual_array.sum(), EPSILON, None)
    return float(np.sum((actual_ratio - expected_ratio) * np.log(actual_ratio / expected_ratio)))


class DriftMonitor:
    """Rolling PSI monitor; it reports only and never triggers retraining."""

    def __init__(self, *, window_size: int = 500, warning_threshold: float = 0.25) -> None:
        self.window_size = window_size
        self.warning_threshold = warning_threshold
        self._features: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._probabilities: deque[float] = deque(maxlen=window_size)
        self._reference = self._load_reference()
        self._lock = RLock()

    @staticmethod
    def _load_reference() -> dict[str, Any]:
        path = (
            Path(config.MODEL_ARTIFACT_DIR)
            / "risk"
            / config.RISK_MODEL_VERSION
            / "metrics.json"
        )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        reference = payload.get("feature_distributions", {})
        return reference if isinstance(reference, dict) else {}

    def record(self, features: dict[str, float], probability: float) -> None:
        with self._lock:
            self._probabilities.append(float(probability))
            for name, value in features.items():
                self._features[name].append(float(value))

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            psi: dict[str, float] = {}
            for name, reference in self._reference.items():
                values = self._features.get(name)
                if not values or not isinstance(reference, dict):
                    continue
                edges = reference.get("bin_edges")
                expected = reference.get("proportions")
                if not isinstance(edges, list) or not isinstance(expected, list):
                    continue
                actual, _ = np.histogram(np.asarray(values, dtype=float), bins=edges)
                if len(actual) != len(expected):
                    continue
                psi[name] = round(population_stability_index(expected, actual.tolist()), 6)
            suspected = sorted(name for name, value in psi.items() if value > self.warning_threshold)
            if suspected:
                LOGGER.warning("drift_suspected", extra={"features": suspected})
            return {
                "window_size": self.window_size,
                "observations": len(self._probabilities),
                "mean_predicted_probability": (
                    round(sum(self._probabilities) / len(self._probabilities), 6)
                    if self._probabilities else None
                ),
                "feature_psi": psi,
                "drift_suspected": bool(suspected),
                "warning_features": suspected,
                "baseline_available": bool(self._reference),
                "automated_action": False,
            }

    def reset(self) -> None:
        with self._lock:
            self._features.clear()
            self._probabilities.clear()


drift_monitor = DriftMonitor()
