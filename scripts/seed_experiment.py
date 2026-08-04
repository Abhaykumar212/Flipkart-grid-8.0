from __future__ import annotations

from datetime import datetime, timezone

from backend import config
from backend.storage.db import SessionLocal
from backend.storage.models import Experiment


EXPERIMENT_ID = "EXP-001"
SPLIT = config.EXPERIMENT_TRAFFIC_SPLIT
NAME = "Personalized intervention vs wishlist reminder"
DESCRIPTION = (
    f"{SPLIT}/{100 - SPLIT} treatment/control test for GRiD 8.0 "
    "cart-abandonment interventions."
)


def seed() -> None:
    with SessionLocal() as db, db.begin():
        experiment = db.get(Experiment, EXPERIMENT_ID)
        if experiment is None:
            db.add(Experiment(
                experiment_id=EXPERIMENT_ID,
                name=NAME,
                description=DESCRIPTION,
                status="RUNNING",
                control_group="CONTROL",
                treatment_group="PERSONALIZED_V1",
                traffic_split=SPLIT,
                discount_budget=0.0,
                started_at=datetime.now(timezone.utc),
            ))
        else:
            experiment.name = NAME
            experiment.description = DESCRIPTION
            experiment.status = "RUNNING"
            experiment.control_group = "CONTROL"
            experiment.treatment_group = "PERSONALIZED_V1"
            experiment.traffic_split = SPLIT


if __name__ == "__main__":
    seed()
    print(f"Seeded {EXPERIMENT_ID} at {SPLIT}/{100 - SPLIT}")
