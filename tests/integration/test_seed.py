import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.storage.db import get_db
from backend.storage.models import InterventionCatalogue, Product, ProductReview
from .conftest import run_command


def _counts(database_url: str) -> tuple[int, int, int]:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        return (
            connection.scalar(select(func.count()).select_from(Product)),
            connection.scalar(select(func.count()).select_from(ProductReview)),
            connection.scalar(select(func.count()).select_from(InterventionCatalogue)),
        )


def test_seed_is_complete_and_idempotent(migrated_database):
    command = [sys.executable, "-m", "scripts.seed_catalog"]
    run_command(command, migrated_database)
    first = _counts(migrated_database)
    run_command(command, migrated_database)
    second = _counts(migrated_database)

    assert first == (50, 300, 12)
    assert second == first


def test_products_api_returns_seeded_catalog(migrated_database):
    run_command([sys.executable, "-m", "scripts.seed_catalog"], migrated_database)
    engine = create_engine(migrated_database, connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            products = client.get("/api/v1/products", params={"category": "mobiles"})
            detail = client.get("/api/v1/products/apple-iphone-16-ultramarine-128gb")
        assert products.status_code == 200
        assert products.json()
        assert all(item["category"] == "mobiles" for item in products.json())
        assert detail.status_code == 200
        assert detail.json()["reviews"]
        assert detail.json()["specifications"]
    finally:
        app.dependency_overrides.clear()
