"""Every frozen scenario must still pass when driven from the in-app demo API.

``test_scenarios.py`` proves the command-line path. This proves the button a
reviewer actually presses, against the same real model artifacts.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def demo_client(tmp_path_factory):
    path = tmp_path_factory.mktemp("demo-api") / "grid8.db"
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

    os.environ["DATABASE_URL"] = database_url
    from backend.main import app

    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("scenario", list("ABCDEFGH"))
def test_scenario_passes_through_the_demo_api(demo_client, scenario):
    body = demo_client.post(f"/api/v1/demo/scenarios/{scenario}/run").json()
    assert body["passed"], body["steps"]
    assert body["steps"]


def test_explanations_never_leak_a_feature_identifier(demo_client):
    import re

    identifier = re.compile(r"\b(?:u|c|p|d|pay|s|x|i)_[a-z_]+\b")
    for scenario in "ABCDEFGH":
        body = demo_client.post(f"/api/v1/demo/scenarios/{scenario}/run").json()
        for step in body["steps"]:
            text = step["rendered_text"] or ""
            assert not identifier.search(text), f"{scenario}: {text}"
            assert "100%" not in text, f"{scenario}: {text}"
