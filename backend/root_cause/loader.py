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
    explainers: list[Any]
    causes: tuple[str, ...]
    thresholds: tuple[float, ...]
    unknown_threshold: float
    version: str


_runtime: Runtime | None = None
_load_error: str | None = None


def load(artifact_path: str | Path | None = None, *, version: str | None = None) -> Runtime:
    global _runtime, _load_error
    if artifact_path is None:
        with SessionLocal() as db:
            row = db.scalar(select(ModelRegistry).where(ModelRegistry.model_type == "ROOT_CAUSE", ModelRegistry.status == "ACTIVE"))
            if row is None:
                raise ArtifactUnavailable("no ACTIVE root-cause model in model_registry")
            artifact_path, version = row.artifact_path, row.model_version
    path = Path(artifact_path)
    required = ("model.joblib", "explainers.joblib", "feature_schema.json", "thresholds.json")
    missing = [name for name in required if not (path / name).exists()]
    if missing:
        raise ArtifactUnavailable(f"root-cause artifacts missing: {', '.join(missing)}")
    if json.loads((path / "feature_schema.json").read_text(encoding="utf-8")) != feature_schema_document():
        raise FeatureSchemaMismatch("root-cause feature schema mismatch")
    settings = json.loads((path / "thresholds.json").read_text(encoding="utf-8"))
    _runtime = Runtime(joblib.load(path / "model.joblib"), joblib.load(path / "explainers.joblib"), tuple(settings["causes"]), tuple(settings["thresholds"]), float(settings["unknown_threshold"]), version or "root_cause-v1")
    _load_error = None
    return _runtime


def runtime() -> Runtime:
    if _runtime is None:
        raise ArtifactUnavailable(_load_error or "root-cause model is not loaded")
    return _runtime


def unload(error: str | None = None) -> None:
    global _runtime, _load_error
    _runtime, _load_error = None, error


def is_ready() -> bool:
    return _runtime is not None


def load_error() -> str | None:
    return _load_error
