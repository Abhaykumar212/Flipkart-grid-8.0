from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.storage.models import SessionFeatureSnapshot

from .schema import FEATURE_SCHEMA_VERSION


def write_feature_snapshot(
    db: Session,
    *,
    session_id: str,
    features: dict[str, float],
    computed_at: datetime | None = None,
    decision_id: str | None = None,
    trigger_event_id: str | None = None,
) -> SessionFeatureSnapshot:
    """Stage one immutable feature snapshot in the caller's transaction."""

    snapshot = SessionFeatureSnapshot(
        snapshot_id=f"FS-{uuid4().hex}",
        session_id=session_id,
        decision_id=decision_id,
        computed_at=computed_at or datetime.now(timezone.utc),
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        features=dict(features),
        trigger_event_id=trigger_event_id,
    )
    db.add(snapshot)
    db.flush()
    return snapshot
