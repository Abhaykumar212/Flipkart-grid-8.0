from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
from sqlalchemy import select

from backend.feature_engine.schema import feature_schema_document
from backend.storage.db import SessionLocal
from backend.storage.models import ModelRegistry


class ArtifactUnavailable(RuntimeError):
    pass


class FeatureSchemaMismatch(RuntimeError):
    pass


@dataclass(frozen=True)
class Runtime:
    model: Any
    calibrator: Any
    explainer: Any
    version: str
    artifact_path: Path


_runtime: Runtime | None = None
_load_error: str | None = None


def load(artifact_path: str | Path | None = None, *, version: str | None = None) -> Runtime:
    global _runtime, _load_error
    if artifact_path is None:
        with SessionLocal() as db:
            row = db.scalar(select(ModelRegistry).where(ModelRegistry.model_type == "RISK", ModelRegistry.status == "ACTIVE"))
            if row is None:
                raise ArtifactUnavailable("no ACTIVE risk model in model_registry")
            artifact_path, version = row.artifact_path, row.model_version
    path = Path(artifact_path)
    required = (path / "model.joblib", path / "calibrator.joblib", path / "explainer.joblib", path / "feature_schema.json")
    missing = [item.name for item in required if not item.exists()]
    if missing:
        raise ArtifactUnavailable(f"risk artifacts missing: {', '.join(missing)}")
    actual = json.loads((path / "feature_schema.json").read_text(encoding="utf-8"))
    if actual != feature_schema_document():
        raise FeatureSchemaMismatch("risk feature_schema.json does not exactly match FEATURE_SCHEMA_V1")
    try:
        _runtime = Runtime(joblib.load(path / "model.joblib"), joblib.load(path / "calibrator.joblib"), joblib.load(path / "explainer.joblib"), version or "risk-v1", path)
        _load_error = None
        return _runtime
    except Exception as error:
        _load_error = str(error)
        raise


def runtime() -> Runtime:
    if _runtime is None:
        raise ArtifactUnavailable(_load_error or "risk model is not loaded")
    return _runtime


def unload(error: str | None = None) -> None:
    global _runtime, _load_error
    _runtime = None
    _load_error = error


def is_ready() -> bool:
    return _runtime is not None


def load_error() -> str | None:
    return _load_error
