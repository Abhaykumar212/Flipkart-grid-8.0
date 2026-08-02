"""Model registry, experiments, feature snapshots, predictions, and decisions."""

from alembic import op

from backend.storage.db import Base
from backend.storage.models import (
    DecisionTrace,
    Experiment,
    InterventionCatalogue,
    ModelPrediction,
    ModelRegistry,
    SessionFeatureSnapshot,
)

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLES = [
    InterventionCatalogue.__table__,
    Experiment.__table__,
    ModelRegistry.__table__,
    DecisionTrace.__table__,
    SessionFeatureSnapshot.__table__,
    ModelPrediction.__table__,
]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=TABLES, checkfirst=False)


def downgrade() -> None:
    connection = op.get_bind()
    for table in reversed(TABLES):
        connection.execute(table.delete())
    Base.metadata.drop_all(bind=connection, tables=TABLES, checkfirst=False)
