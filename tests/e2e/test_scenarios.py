from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def scenario_database(tmp_path_factory):
    path = tmp_path_factory.mktemp("scenarios") / "grid8.db"
    database_url = f"sqlite:///{path.as_posix()}"
    environment = os.environ.copy()
    environment.update({
        "DATABASE_URL": database_url,
        "LOG_LEVEL": "ERROR",
        "PYTHONIOENCODING": "utf-8",
    })
    commands = (
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        [sys.executable, "-m", "scripts.seed_catalog"],
        [sys.executable, "-m", "scripts.seed_experiment"],
        [sys.executable, "-m", "ml.training.registry", "promote", "--model", "risk", "--version", "v1"],
        [sys.executable, "-m", "ml.training.registry", "promote", "--model", "root_cause", "--version", "v1"],
        [sys.executable, "-m", "scripts.warm_review_cache"],
    )
    for command in commands:
        subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=True)
    return environment


@pytest.mark.parametrize("scenario", list("ABCDEFGH"))
def test_scenario_matches_frozen_expectation(scenario_database, scenario):
    result = subprocess.run(
        [sys.executable, "-m", "scripts.run_scenario", scenario],
        cwd=PROJECT_ROOT,
        env=scenario_database,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f'"scenario": "{scenario}"' in result.stdout
