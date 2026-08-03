from datetime import datetime, timezone

from backend.experimentation.metrics import experiment_metrics
from backend.storage.models import Experiment, ExperimentAssignment, ShoppingSession


def test_experiment_metrics_reports_inconclusive_empty_arms(api_harness) -> None:
    with api_harness.sessions() as db, db.begin():
        result = experiment_metrics(db, "EXP-001")
    assert result is not None
    assert result["uplift"]["label"] == "inconclusive"
    assert result["uplift"]["relative"] is None


def test_experiment_metrics_uplift_ci_arithmetic(api_harness) -> None:
    now = datetime.now(timezone.utc)
    with api_harness.sessions() as db, db.begin():
        experiment = db.get(Experiment, "EXP-001")
        assert experiment is not None
        for index in range(20):
            db.add(ShoppingSession(
                session_id=f"m-control-{index}",
                started_at=now,
                outcome="OPEN",
            ))
            db.add(ShoppingSession(
                session_id=f"m-treatment-{index}",
                started_at=now,
                outcome="OPEN",
            ))
        db.flush()
        for index in range(20):
            db.add(ExperimentAssignment(
                assignment_id=f"test-control-{index}",
                experiment_id="EXP-001",
                session_id=f"m-control-{index}",
                group_name="CONTROL",
                assigned_at=now,
            ))
            db.add(ExperimentAssignment(
                assignment_id=f"test-treatment-{index}",
                experiment_id="EXP-001",
                session_id=f"m-treatment-{index}",
                group_name="PERSONALIZED_V1",
                assigned_at=now,
            ))
        result = experiment_metrics(db, "EXP-001")
    assert result is not None
    assert result["arms"]["CONTROL"]["sessions"] == 20
    assert result["arms"]["PERSONALIZED_V1"]["sessions"] == 20
    assert result["uplift"]["ci95"] is not None
