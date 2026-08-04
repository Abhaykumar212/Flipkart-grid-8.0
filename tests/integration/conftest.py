import os
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.deps import get_session_store
from backend.domain.causes import RootCause
from backend.domain.enums import RiskBand
from backend.main import app
from backend.risk_model.contracts import RiskFactor, RiskPrediction
from backend.root_cause.contracts import CausePrediction, CauseResult
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


def _integration_risk(features: dict[str, float]) -> RiskPrediction:
    """Stable model boundary for API integration tests.

    Artifact loading, schema compatibility, metrics, and inference behavior are
    covered by tests/model. Integration tests exercise orchestration and
    persistence without depending on ignored local joblib files.
    """

    has_cart = features["s_cart_add_count"] > 0 and features["c_item_count"] > 0
    if not has_cart:
        probability = 0.12
        factors = (RiskFactor("s_cart_add_count", features["s_cart_add_count"], -0.4),)
    elif features["pay_failure_count"] > 0:
        probability = 0.88
        factors = (
            RiskFactor("pay_failure_count", features["pay_failure_count"], 0.4),
            RiskFactor("pay_method_change_count", features["pay_method_change_count"], 0.2),
            RiskFactor("pay_checkout_max_step", features["pay_checkout_max_step"], -0.15),
        )
    else:
        probability = 0.82
        factors = (
            RiskFactor("s_review_open_count", features["s_review_open_count"], 0.35),
            RiskFactor("s_similar_product_view_count", features["s_similar_product_view_count"], 0.25),
            RiskFactor("s_review_dwell_seconds", features["s_review_dwell_seconds"], 0.15),
        )
    band = RiskBand.HIGH if probability >= 0.70 else RiskBand.LOW
    return RiskPrediction(
        probability=probability,
        confidence=min(1.0, abs(probability - 0.5) * 2),
        band=band,
        model_version="risk-integration-v1",
        top_factors=factors,
        latency_ms=1.0,
    )


def _integration_causes(features: dict[str, float]) -> CauseResult:
    if features["pay_failure_count"] > 0:
        prediction = CausePrediction(
            RootCause.CHECKOUT_OR_PAYMENT_FAILURE,
            0.90,
            ("pay_failure_count", "pay_method_change_count", "pay_checkout_max_step"),
        )
    else:
        prediction = CausePrediction(
            RootCause.PRODUCT_QUALITY_UNCERTAINTY,
            0.90,
            ("s_review_open_count", "s_similar_product_view_count", "s_review_dwell_seconds"),
        )
    return CauseResult((prediction,), "root-cause-integration-v1", False, 0.90, 1.0)


@pytest.fixture
def api_harness(migrated_database, monkeypatch):
    run_command([sys.executable, "-m", "scripts.seed_catalog"], migrated_database)
    # Migration 0008 seeds a fixed split; this brings the row up to the
    # configured one, exactly as reset_demo does. Without it the replayer picks
    # session ids for an arm using one split while the pipeline buckets with
    # another, and scenario H stops demonstrating both arms.
    run_command([sys.executable, "-m", "scripts.seed_experiment"], migrated_database)
    run_command([sys.executable, "-m", "scripts.warm_review_cache"], migrated_database)
    engine = build_engine(migrated_database)
    testing_sessions = sessionmaker(bind=engine, expire_on_commit=False)
    store = InMemorySessionStore()

    def override_db():
        with testing_sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_session_store] = lambda: store
    monkeypatch.setattr("backend.main._load_artifacts", lambda: None)
    monkeypatch.setattr("backend.main.risk_loader.load", lambda: None)
    monkeypatch.setattr("backend.main.root_cause_loader.load", lambda: None)
    monkeypatch.setattr("backend.orchestrator.pipeline.predict_risk", _integration_risk)
    monkeypatch.setattr("backend.orchestrator.pipeline.predict_root_causes", _integration_causes)
    try:
        with TestClient(app) as client:
            yield ApiHarness(client, testing_sessions, store)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
