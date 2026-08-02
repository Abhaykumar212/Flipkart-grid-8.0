import os
from pathlib import Path
import subprocess
import sys

import pytest

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
