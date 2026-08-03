from __future__ import annotations

from collections import Counter, defaultdict, deque
from math import ceil
from threading import RLock
from typing import Iterable


def _percentile(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, ceil(percentile * len(ordered)) - 1))
    return round(ordered[index], 3)


class MetricsRegistry:
    """Small bounded metrics registry suitable for the single-process demo."""

    def __init__(self, *, histogram_size: int = 5_000) -> None:
        self._counters: Counter[str] = Counter()
        self._labelled: dict[str, Counter[str]] = defaultdict(Counter)
        self._histograms: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=histogram_size)
        )
        self._gauges: dict[str, float] = {}
        self._lock = RLock()

    def increment(self, name: str, amount: int = 1, *, label: str | None = None) -> None:
        with self._lock:
            self._counters[name] += amount
            if label is not None:
                self._labelled[name][label] += amount

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms[name].append(float(value))

    def gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = float(value)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            counters = {
                name: {
                    "total": total,
                    "by_label": dict(sorted(self._labelled.get(name, {}).items())),
                }
                for name, total in sorted(self._counters.items())
            }
            latency = {
                name: {
                    "count": len(values),
                    "p50": _percentile(values, 0.50),
                    "p95": _percentile(values, 0.95),
                    "p99": _percentile(values, 0.99),
                    "max": round(max(values), 3) if values else 0.0,
                }
                for name, values in sorted(self._histograms.items())
            }
            return {
                "counters": counters,
                "latency_ms": latency,
                "gauges": dict(sorted(self._gauges.items())),
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._labelled.clear()
            self._histograms.clear()
            self._gauges.clear()


metrics_registry = MetricsRegistry()
