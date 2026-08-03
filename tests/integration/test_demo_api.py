"""The in-app demo controls are judge-facing, so they get the same rigour.

Cause-level expectations depend on the real models and are asserted end to end in
``tests/e2e/test_demo_scenarios.py``. What is checked here is the machinery:
endpoint shape, repeat-run independence, request validation, and that traffic
simulation actually fills both experiment arms instead of starving control.
"""

import pytest

from backend.demo.fixtures import SCENARIO_LETTERS, scenario_catalogue
from backend.demo.simulate import CAUSE_MATCHED, RESPONSE_MODEL


def test_catalogue_describes_every_frozen_scenario():
    catalogue = scenario_catalogue()
    assert [item["scenario"] for item in catalogue] == list(SCENARIO_LETTERS)
    for item in catalogue:
        assert item["title"] and item["proves"] and item["detail"]
        assert item["event_count"] > 0
        assert item["expectations"]


def test_scenarios_endpoint_lists_all_eight(api_harness):
    body = api_harness.client.get("/api/v1/demo/scenarios").json()
    assert body["count"] == 8
    assert {item["scenario"] for item in body["scenarios"]} == set(SCENARIO_LETTERS)


@pytest.mark.parametrize("letter", SCENARIO_LETTERS)
def test_every_scenario_runs_through_the_real_pipeline(api_harness, letter):
    body = api_harness.client.post(f"/api/v1/demo/scenarios/{letter}/run").json()
    assert body["scenario"] == letter
    assert body["steps"], "a scenario must produce at least one decision"
    for step in body["steps"]:
        assert step["decision"] in {"INTERVENE", "NO_ACTION", "ABSTAIN"}
    # Multi-decision scenarios only pin the final state, so the expectation
    # rides on the last step rather than on every one.
    assert any(step["expected"] for step in body["steps"])


def test_unknown_scenario_is_rejected(api_harness):
    assert api_harness.client.post("/api/v1/demo/scenarios/Z/run").status_code == 404


def test_repeat_runs_do_not_collide(api_harness):
    first = api_harness.client.post("/api/v1/demo/scenarios/A/run").json()
    second = api_harness.client.post("/api/v1/demo/scenarios/A/run").json()
    assert first["steps"][0]["session_id"] != second["steps"][0]["session_id"]
    assert first["steps"][0]["decision_id"] != second["steps"][0]["decision_id"]


def test_scenario_h_still_demonstrates_both_arms(api_harness):
    body = api_harness.client.post("/api/v1/demo/scenarios/H/run").json()
    assert {step["experiment_group"] for step in body["steps"]} == {
        "CONTROL", "PERSONALIZED_V1"
    }


def test_simulation_fills_both_experiment_arms(api_harness):
    result = api_harness.client.post(
        "/api/v1/demo/simulate", json={"sessions": 16, "seed": 3}
    ).json()
    assert result["totals"]["sessions"] == 16
    assert result["totals"]["decisions"] >= 16
    assert result["response_model"], "the assumptions must travel with the numbers"
    assert result["disclaimer"]

    metrics = api_harness.client.get(
        "/api/v1/dashboard/experiments/EXP-001/metrics"
    ).json()
    # Forcing arms here would starve control and make any uplift meaningless.
    assert all(arm["sessions"] > 0 for arm in metrics["arms"].values())


def test_simulation_records_outcomes_for_every_decision(api_harness):
    result = api_harness.client.post(
        "/api/v1/demo/simulate", json={"sessions": 8, "seed": 5}
    ).json()
    totals = result["totals"]
    assert totals["shown"] > 0
    assert totals["clicked"] + totals["dismissed"] <= totals["shown"]


def test_simulation_rejects_an_unbounded_request(api_harness):
    response = api_harness.client.post("/api/v1/demo/simulate", json={"sessions": 10_000})
    assert response.status_code == 422


def test_response_model_treats_control_as_generic():
    # The control arm shows one fixed reminder regardless of diagnosis, so its
    # label lining up with a cause must not earn it the matched response rate.
    assert "WISHLIST_REMINDER" in CAUSE_MATCHED["LOW_PURCHASE_INTENT"]
    assert RESPONSE_MODEL.click_rate(matched=True) > RESPONSE_MODEL.click_rate(matched=False)
    assert RESPONSE_MODEL.dismissal_rate(matched=True) < RESPONSE_MODEL.dismissal_rate(matched=False)


def test_conversion_baseline_follows_calibrated_risk():
    low = RESPONSE_MODEL.conversion_rate(
        abandonment_probability=0.1, shown=False, clicked=False, dismissed=False, matched=False
    )
    high = RESPONSE_MODEL.conversion_rate(
        abandonment_probability=0.9, shown=False, clicked=False, dismissed=False, matched=False
    )
    assert low > high, "a session the agent left alone still converts on its own merits"

    dismissed = RESPONSE_MODEL.conversion_rate(
        abandonment_probability=0.8, shown=True, clicked=False, dismissed=True, matched=False
    )
    untouched = RESPONSE_MODEL.conversion_rate(
        abandonment_probability=0.8, shown=False, clicked=False, dismissed=False, matched=False
    )
    assert dismissed < untouched, "over-serving has to cost something"
