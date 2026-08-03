from __future__ import annotations

from datetime import datetime, timezone

from backend.storage.db import SessionLocal
from backend.storage.models import Experiment


EXPERIMENT_ID = "EXP-001"


def seed() -> None:
    with SessionLocal() as db, db.begin():
        experiment = db.get(Experiment, EXPERIMENT_ID)
        if experiment is None:
            db.add(Experiment(
                experiment_id=EXPERIMENT_ID,
                name="Personalized intervention vs wishlist reminder",
                description="50/50 control-arm test for GRiD 8.0 cart-abandonment interventions.",
                status="RUNNING",
                control_group="CONTROL",
                treatment_group="PERSONALIZED_V1",
                traffic_split=50,
                discount_budget=0.0,
                started_at=datetime.now(timezone.utc),
            ))
        else:
            experiment.name = "Personalized intervention vs wishlist reminder"
            experiment.description = "50/50 control-arm test for GRiD 8.0 cart-abandonment interventions."
            experiment.status = "RUNNING"
            experiment.control_group = "CONTROL"
            experiment.treatment_group = "PERSONALIZED_V1"
            experiment.traffic_split = 50


if __name__ == "__main__":
    seed()
    print(f"Seeded {EXPERIMENT_ID}")
