from backend.observability.latency import MetricsRegistry


def test_decision_latency_histogram_enforces_p95_budget():
    registry = MetricsRegistry()
    for latency in range(100, 200):
        registry.observe("decision_total", latency)
    histogram = registry.snapshot()["latency_ms"]["decision_total"]
    assert histogram["p95"] < 300
