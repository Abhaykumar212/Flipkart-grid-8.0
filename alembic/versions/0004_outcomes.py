"""Intervention impressions/outcomes and completed orders."""

from alembic import op

from backend.storage.db import Base
from backend.storage.models import InterventionImpression, InterventionOutcome, Order

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TABLES = [InterventionImpression.__table__, InterventionOutcome.__table__, Order.__table__]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=TABLES, checkfirst=False)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=TABLES, checkfirst=False)
