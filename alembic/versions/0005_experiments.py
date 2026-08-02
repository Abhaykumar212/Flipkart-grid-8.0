"""Deterministic experiment assignments."""

from alembic import op

from backend.storage.models import ExperimentAssignment

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ExperimentAssignment.__table__.create(bind=op.get_bind(), checkfirst=False)


def downgrade() -> None:
    ExperimentAssignment.__table__.drop(bind=op.get_bind(), checkfirst=False)
