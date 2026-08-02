"""Core users, catalog, sessions, and carts."""

from alembic import op

from backend.storage.db import Base
from backend.storage.models import (
    Cart,
    CartItem,
    Product,
    ProductReview,
    ProductReviewSummary,
    ShoppingSession,
    User,
)

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLES = [
    User.__table__,
    Product.__table__,
    ProductReview.__table__,
    ProductReviewSummary.__table__,
    ShoppingSession.__table__,
    Cart.__table__,
    CartItem.__table__,
]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=TABLES, checkfirst=False)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=TABLES, checkfirst=False)
