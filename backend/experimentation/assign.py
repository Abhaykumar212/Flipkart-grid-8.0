from hashlib import sha256
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import config
from backend.storage.models import Experiment, ExperimentAssignment


DEFAULT_EXPERIMENT_ID = "EXP-001"


def assignment_bucket(session_id: str, experiment_id: str) -> int:
    digest = sha256(f"{session_id}:{experiment_id}".encode()).hexdigest()
    return int(digest[:8], 16) % 100


def assign_group(
    session_id: str,
    experiment_id: str,
    *,
    # Defaults to the configured split so a caller without the Experiment row —
    # the scenario replayer choosing a session id for a required arm — buckets
    # sessions exactly the way the pipeline will.
    traffic_split: int = config.EXPERIMENT_TRAFFIC_SPLIT,
    control_group: str = "CONTROL",
    treatment_group: str = "PERSONALIZED_V1",
) -> str:
    if not 0 <= traffic_split <= 100:
        raise ValueError("traffic_split must be between 0 and 100")
    return (
        treatment_group
        if assignment_bucket(session_id, experiment_id) < traffic_split
        else control_group
    )


def active_experiment(db: Session, experiment_id: str = DEFAULT_EXPERIMENT_ID) -> Experiment | None:
    return db.scalar(
        select(Experiment).where(
            Experiment.experiment_id == experiment_id,
            Experiment.status == "RUNNING",
        )
    )


def get_or_assign(
    db: Session,
    session_id: str,
    experiment: Experiment,
    *,
    now: datetime | None = None,
) -> ExperimentAssignment:
    existing = db.scalar(
        select(ExperimentAssignment).where(
            ExperimentAssignment.experiment_id == experiment.experiment_id,
            ExperimentAssignment.session_id == session_id,
        )
    )
    if existing is not None:
        return existing
    assignment = ExperimentAssignment(
        assignment_id=f"EA-{uuid4().hex}",
        experiment_id=experiment.experiment_id,
        session_id=session_id,
        group_name=assign_group(
            session_id,
            experiment.experiment_id,
            traffic_split=experiment.traffic_split,
            control_group=experiment.control_group,
            treatment_group=experiment.treatment_group,
        ),
        assigned_at=now or datetime.now(timezone.utc),
    )
    db.add(assignment)
    db.flush()
    return assignment
