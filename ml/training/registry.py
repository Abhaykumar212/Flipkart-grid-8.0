from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from backend.feature_engine.schema import FEATURE_SCHEMA_VERSION
from backend.storage.db import SessionLocal
from backend.storage.models import ModelRegistry


def _identity(model: str, version: str) -> tuple[str, str, Path]:
    normalized = version if version.startswith(f"{model}-") else f"{model}-{version}"
    return model, normalized, Path("ml/artifacts") / model / version.removeprefix(f"{model}-")


def promote(model: str, version: str) -> ModelRegistry:
    name, normalized, artifact = _identity(model, version)
    metrics = json.loads((artifact / "metrics.json").read_text(encoding="utf-8"))
    model_type = "RISK" if model == "risk" else "ROOT_CAUSE"
    with SessionLocal.begin() as db:
        active = db.scalars(select(ModelRegistry).where(ModelRegistry.model_type == model_type, ModelRegistry.status == "ACTIVE")).all()
        for row in active:
            row.status = "ROLLED_BACK"
        row = db.scalar(select(ModelRegistry).where(ModelRegistry.model_name == name, ModelRegistry.model_version == normalized))
        if row is None:
            row = ModelRegistry(model_id=f"mdl_{uuid4().hex}", model_name=name, model_version=normalized, model_type=model_type, artifact_path=str(artifact.resolve()), feature_schema_version=FEATURE_SCHEMA_VERSION, training_data_version="simulator-v1", trained_at=datetime.now(timezone.utc), metrics=metrics, status="ACTIVE", promoted_at=datetime.now(timezone.utc))
            db.add(row)
        else:
            row.status = "ACTIVE"
            row.promoted_at = datetime.now(timezone.utc)
            row.artifact_path = str(artifact.resolve())
            row.metrics = metrics
        db.flush()
        return row


def rollback(model: str, version: str | None = None) -> ModelRegistry:
    model_type = "RISK" if model == "risk" else "ROOT_CAUSE"
    with SessionLocal.begin() as db:
        current = db.scalar(select(ModelRegistry).where(ModelRegistry.model_type == model_type, ModelRegistry.status == "ACTIVE"))
        query = select(ModelRegistry).where(ModelRegistry.model_type == model_type, ModelRegistry.status == "ROLLED_BACK")
        if version:
            _, normalized, _ = _identity(model, version)
            query = query.where(ModelRegistry.model_version == normalized)
        target = db.scalar(query.order_by(ModelRegistry.promoted_at.desc()).limit(1))
        if target is None:
            raise RuntimeError(f"no rollback target for {model}")
        if current:
            current.status = "ROLLED_BACK"
        target.status = "ACTIVE"
        target.promoted_at = datetime.now(timezone.utc)
        db.flush()
        return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("promote", "rollback"))
    parser.add_argument("--model", choices=("risk", "root_cause"), required=True)
    parser.add_argument("--version")
    args = parser.parse_args()
    if args.command == "promote" and not args.version:
        parser.error("promote requires --version")
    row = promote(args.model, args.version) if args.command == "promote" else rollback(args.model, args.version)
    print(f"{row.model_name} {row.model_version} -> {row.status}")


if __name__ == "__main__":
    main()
