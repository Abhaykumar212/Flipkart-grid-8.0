import os
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.deps import get_session_store
from backend.main import app
from backend.storage.db import build_engine, get_db
from backend.storage.session_store import InMemorySessionStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def run_command(arguments: list[str], database_url: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(arguments, cwd=PROJECT_ROOT, env=environment, check=True)


def run_alembic(database_url: str, *arguments: str) -> None:
    run_command([sys.executable, "-m", "alembic", *arguments], database_url)


@pytest.fixture
def migrated_database(tmp_path):
    database_url = sqlite_url(tmp_path / "grid8-test.db")
    run_alembic(database_url, "upgrade", "head")
    return database_url


@dataclass(slots=True)
class ApiHarness:
    client: TestClient
    sessions: sessionmaker
    store: InMemorySessionStore


@pytest.fixture
def api_harness(migrated_database, monkeypatch):
    run_command([sys.executable, "-m", "scripts.seed_catalog"], migrated_database)
    engine = build_engine(migrated_database)
    testing_sessions = sessionmaker(bind=engine, expire_on_commit=False)
    store = InMemorySessionStore()

    def override_db():
        with testing_sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_session_store] = lambda: store
    monkeypatch.setattr("backend.main._load_artifacts", lambda: None)
    try:
        with TestClient(app) as client:
            yield ApiHarness(client, testing_sessions, store)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
