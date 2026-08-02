"""Append-only behavioral event stream."""

from alembic import op

from backend.storage.models import Event

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Event.__table__.create(bind=op.get_bind(), checkfirst=False)


def downgrade() -> None:
    Event.__table__.drop(bind=op.get_bind(), checkfirst=False)
