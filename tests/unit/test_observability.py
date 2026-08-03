from backend.observability.drift import DriftMonitor, population_stability_index
from backend.observability.latency import MetricsRegistry
from backend.observability.rate_limit import SlidingWindowRateLimiter


def test_metrics_registry_reports_labelled_counters_and_percentiles():
    registry = MetricsRegistry()
    registry.increment("decisions", label="INTERVENE")
    for value in range(1, 101):
        registry.observe("decision_total", value)
    snapshot = registry.snapshot()
    assert snapshot["counters"]["decisions"]["by_label"] == {"INTERVENE": 1}
    assert snapshot["latency_ms"]["decision_total"]["p95"] == 95


def test_rate_limiter_returns_retry_after_and_recovers_after_window():
    limiter = SlidingWindowRateLimiter(window_seconds=60)
    assert limiter.acquire("s1", limit=2, now=0).allowed
    assert limiter.acquire("s1", limit=2, now=1).allowed
    rejected = limiter.acquire("s1", limit=2, now=2)
    assert not rejected.allowed and rejected.retry_after_seconds > 0
    assert limiter.acquire("s1", limit=2, now=61).allowed


def test_drift_monitor_reports_without_automated_action():
    assert population_stability_index([50, 50], [50, 50]) == 0
    monitor = DriftMonitor(window_size=3)
    monitor.record({"c_value": 1000}, 0.8)
    snapshot = monitor.snapshot()
    assert snapshot["observations"] == 1
    assert snapshot["mean_predicted_probability"] == 0.8
    assert snapshot["automated_action"] is False
