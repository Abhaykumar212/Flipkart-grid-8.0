"""Validate catalogue requirements and add experiment discount budgets."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "discount_budget" not in {column["name"] for column in inspector.get_columns("experiments")}:
        op.add_column("experiments", sa.Column("discount_budget", sa.Float(), nullable=False, server_default="0"))
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("intervention_catalogue") as batch:
            batch.create_check_constraint("ck_catalogue_requires_json_array", "json_valid(requires) AND json_type(requires) = 'array'")
    else:
        op.create_check_constraint("ck_catalogue_requires_json_array", "intervention_catalogue", "jsonb_typeof(requires::jsonb) = 'array'")


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("intervention_catalogue") as batch:
            batch.drop_constraint("ck_catalogue_requires_json_array", type_="check")
    else:
        op.drop_constraint("ck_catalogue_requires_json_array", "intervention_catalogue", type_="check")
    if "discount_budget" in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("experiments")}:
        op.drop_column("experiments", "discount_budget")
