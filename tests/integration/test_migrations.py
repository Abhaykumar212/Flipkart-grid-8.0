from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, create_mock_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from backend.storage.db import Base
from backend.storage import models  # noqa: F401
from .conftest import run_alembic, sqlite_url

APPLICATION_TABLES = {
    "users",
    "products",
    "product_reviews",
    "product_review_summaries",
    "sessions",
    "carts",
    "cart_items",
    "events",
    "session_feature_snapshots",
    "model_predictions",
    "decision_traces",
    "intervention_catalogue",
    "intervention_impressions",
    "intervention_outcomes",
    "orders",
    "experiments",
    "experiment_assignments",
    "model_registry",
}


def test_upgrade_and_downgrade_clean(tmp_path):
    database_url = sqlite_url(tmp_path / "migration-roundtrip.db")
    run_alembic(database_url, "upgrade", "head")
    engine = create_engine(database_url)
    assert set(inspect(engine).get_table_names()) - {"alembic_version"} == APPLICATION_TABLES

    run_alembic(database_url, "downgrade", "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}


def test_foreign_keys_and_closed_enums_are_enforced(migrated_database):
    engine = create_engine(migrated_database)
    now = datetime.now(timezone.utc).isoformat()
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.execute(text(
            "INSERT INTO sessions "
            "(session_id, started_at, is_returning_user, outcome, is_synthetic) "
            "VALUES ('s1', :now, 0, 'OPEN', 1)"
        ), {"now": now})
        connection.execute(text(
            "INSERT INTO carts "
            "(cart_id, session_id, created_at, updated_at, cart_value, mrp_total, delivery_fee, item_count) "
            "VALUES ('c1', 's1', :now, :now, 10, 10, 0, 1)"
        ), {"now": now})

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.execute(text(
                "INSERT INTO cart_items "
                "(cart_item_id, cart_id, product_id, quantity, unit_price, added_at) "
                "VALUES ('ci1', 'c1', 'missing-product', 1, 10, :now)"
            ), {"now": now})

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO events "
                "(event_id, session_id, event_type, sequence_no, client_timestamp, server_timestamp, metadata, is_late) "
                "VALUES ('e1', 's1', 'INVALID', 1, :now, :now, '{}', 0)"
            ), {"now": now})


def test_schema_has_expected_keys_constraints_and_indexes(migrated_database):
    schema = inspect(create_engine(migrated_database))
    for table in APPLICATION_TABLES:
        assert schema.get_pk_constraint(table)["constrained_columns"], table

    expected_indexes = {
        "ix_users_persona",
        "ix_products_category",
        "ix_products_brand",
        "ix_reviews_product_rating",
        "ix_reviews_product_helpful",
        "ix_sessions_user",
        "ix_sessions_started",
        "ix_sessions_outcome",
        "ux_cart_items_active",
        "ix_events_session_time",
        "ix_events_type_time",
        "ix_snapshots_session_time",
        "ix_predictions_model",
        "ix_traces_session_time",
        "ix_traces_decision",
        "ix_traces_experiment",
        "ux_model_registry_active_type",
    }
    actual_indexes = {
        index["name"]
        for table in APPLICATION_TABLES
        for index in schema.get_indexes(table)
    }
    assert expected_indexes <= actual_indexes

    assert len(schema.get_foreign_keys("cart_items")) == 2
    assert len(schema.get_foreign_keys("events")) == 3
    assert len(schema.get_foreign_keys("decision_traces")) == 4
    assert len(schema.get_foreign_keys("model_predictions")) == 3

    named_unique_constraints = {
        constraint["name"]
        for table in APPLICATION_TABLES
        for constraint in schema.get_unique_constraints(table)
    }
    assert {
        "ux_review_summary_version",
        "ux_events_session_seq",
        "ux_model_registry_version",
        "ux_assignment_session",
    } <= named_unique_constraints


def test_only_one_active_model_per_type(migrated_database):
    engine = create_engine(migrated_database)
    values = {
        "artifact": "./model.joblib",
        "schema": "fs-v1",
        "data": "seed-1",
        "trained": datetime.now(timezone.utc).isoformat(),
        "metrics": "{}",
    }
    insert = text(
        "INSERT INTO model_registry "
        "(model_id, model_name, model_version, model_type, artifact_path, feature_schema_version, "
        "training_data_version, trained_at, metrics, status) "
        "VALUES (:id, :name, :version, 'RISK', :artifact, :schema, :data, :trained, :metrics, 'ACTIVE')"
    )
    with engine.begin() as connection:
        connection.execute(insert, {**values, "id": "m1", "name": "risk", "version": "v1"})
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(insert, {**values, "id": "m2", "name": "risk", "version": "v2"})


def test_schema_compiles_for_postgres_without_dialect_specific_types():
    statements: list[str] = []
    engine = None

    def capture(sql, *args, **kwargs):
        statements.append(str(sql.compile(dialect=engine.dialect)))

    engine = create_mock_engine("postgresql+psycopg://", capture)
    Base.metadata.create_all(engine, checkfirst=False)
    ddl = "\n".join(statements)
    assert "CREATE TABLE products" in ddl
    assert "CREATE TABLE decision_traces" in ddl
    assert "JSONB" not in ddl
    assert "AUTOINCREMENT" not in ddl
