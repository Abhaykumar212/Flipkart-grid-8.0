"""Seed EXP-001 personalization experiment."""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


experiments = sa.table(
    "experiments",
    sa.column("experiment_id", sa.String()),
    sa.column("name", sa.String()),
    sa.column("description", sa.Text()),
    sa.column("status", sa.String()),
    sa.column("control_group", sa.String()),
    sa.column("treatment_group", sa.String()),
    sa.column("traffic_split", sa.Integer()),
    sa.column("discount_budget", sa.Float()),
    sa.column("started_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.bulk_insert(
        experiments,
        [{
            "experiment_id": "EXP-001",
            "name": "Personalized intervention vs wishlist reminder",
            "description": "50/50 control-arm test for GRiD 8.0 cart-abandonment interventions.",
            "status": "RUNNING",
            "control_group": "CONTROL",
            "treatment_group": "PERSONALIZED_V1",
            "traffic_split": 50,
            "discount_budget": 0.0,
            "started_at": datetime.now(timezone.utc),
        }],
    )


def downgrade() -> None:
    op.execute(experiments.delete().where(experiments.c.experiment_id == "EXP-001"))
