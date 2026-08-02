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
        # Recreating this referenced table fails on populated SQLite databases.
        # Triggers provide the same validation without dropping the parent table.
        op.execute("DROP TABLE IF EXISTS _alembic_tmp_intervention_catalogue")
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS ck_catalogue_requires_json_array_insert
            BEFORE INSERT ON intervention_catalogue
            WHEN json_valid(NEW.requires) = 0 OR json_type(NEW.requires) != 'array'
            BEGIN SELECT RAISE(ABORT, 'intervention_catalogue.requires must be a JSON array'); END
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS ck_catalogue_requires_json_array_update
            BEFORE UPDATE OF requires ON intervention_catalogue
            WHEN json_valid(NEW.requires) = 0 OR json_type(NEW.requires) != 'array'
            BEGIN SELECT RAISE(ABORT, 'intervention_catalogue.requires must be a JSON array'); END
        """)
    else:
        op.create_check_constraint("ck_catalogue_requires_json_array", "intervention_catalogue", "jsonb_typeof(requires::jsonb) = 'array'")


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS ck_catalogue_requires_json_array_insert")
        op.execute("DROP TRIGGER IF EXISTS ck_catalogue_requires_json_array_update")
    else:
        op.drop_constraint("ck_catalogue_requires_json_array", "intervention_catalogue", type_="check")
    if "discount_budget" in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("experiments")}:
        op.drop_column("experiments", "discount_budget")
