"""Run frozen scenarios through the real decision path, in-process.

This deliberately reuses ``ingest_events`` and ``run_decision`` rather than
faking results: a scenario that passes here passes because the production code
path produced it. Each run mints fresh session identifiers so a reviewer can
press the button repeatedly without resetting the database.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from time import perf_counter
from typing import Any, Iterator
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy.orm import Session, sessionmaker

from backend import config
from backend.domain.events import EventEnvelope
from backend.event_ingestion.ingest import ingest_events
from backend.experimentation.assign import DEFAULT_EXPERIMENT_ID, assign_group
from backend.orchestrator.persist import persist_decision
from backend.orchestrator.pipeline import run_decision
from backend.storage.models import User
from backend.storage.session_store import SessionStore

from .fixtures import SCENARIO_INTENT, load_fixture

_event_adapter = TypeAdapter(list[EventEnvelope])

#: Bound on the search for a session id that lands in a required A/B arm.
_MAX_ARM_ATTEMPTS = 200


def deterministic_uuid(key: str) -> str:
    """A stable UUIDv4-shaped identifier derived from a key."""

    value = bytearray(sha256(key.encode()).digest()[:16])
    value[6] = (value[6] & 0x0F) | 0x40
    value[8] = (value[8] & 0x3F) | 0x80
    return str(UUID(bytes=bytes(value)))


@contextmanager
def _immediate_decisions() -> Iterator[None]:
    """Drop the interactive debounce for the length of a replay.

    The debounce exists to stop a live browser from asking the pipeline the same
    question twice per second. A replay is one explicit operator request, so it
    would otherwise stall on its own event timestamps.
    """

    previous = config.DECISION_DEBOUNCE_SECONDS
    config.DECISION_DEBOUNCE_SECONDS = 0
    try:
        yield
    finally:
        config.DECISION_DEBOUNCE_SECONDS = previous


def _session_id_for_arm(base: str, run_key: str, required_group: str | None) -> str:
    """Mint a fresh session id, honouring a required experiment arm.

    Assignment hashes the session id, so a randomly minted id would scramble the
    arm that scenario H exists to demonstrate. Searching for a suffix that lands
    in the required bucket keeps the demonstration intact while still making
    every run independent.
    """

    if required_group is None:
        return f"{base}-{run_key}"
    for attempt in range(_MAX_ARM_ATTEMPTS):
        candidate = f"{base}-{run_key}{attempt or ''}"
        if assign_group(candidate, DEFAULT_EXPERIMENT_ID) == required_group:
            return candidate
    return f"{base}-{run_key}"


@dataclass(slots=True)
class ReplayStep:
    """One decision produced during a replay, with its verdict."""

    session_id: str
    trigger: str
    decision_id: str | None
    decision: str | None
    intervention: str | None
    dominant_cause: str | None
    probability: float | None
    confidence: float | None
    experiment_group: str | None
    channel: str | None
    rendered_text: str | None
    expected: dict[str, Any] = field(default_factory=dict)
    mismatches: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.mismatches

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "trigger": self.trigger,
            "decision_id": self.decision_id,
            "decision": self.decision,
            "intervention": self.intervention,
            "dominant_cause": self.dominant_cause,
            "probability": self.probability,
            "confidence": self.confidence,
            "experiment_group": self.experiment_group,
            "channel": self.channel,
            "rendered_text": self.rendered_text,
            "expected": self.expected,
            "mismatches": self.mismatches,
            "passed": self.passed,
        }


def _actual(response: dict[str, Any]) -> dict[str, Any]:
    causes = response.get("root_causes") or []
    recommended = response.get("recommended_intervention") or {}
    return {
        "decision": response.get("decision"),
        "intervention": recommended.get("type"),
        "dominant_cause": causes[0].get("cause") if causes else None,
        "experiment_group": response.get("experiment_group"),
    }


def _compare(response: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    actual = _actual(response)
    return {
        key: {"expected": value, "actual": actual.get(key)}
        for key, value in expected.items()
        if actual.get(key) != value
    }


def ingest(db: Session, store: SessionStore, payloads: list[dict[str, Any]]) -> None:
    """Ingest a batch through the real path.

    ``ingest_events`` opens its own transaction, so any implicit one this
    session picked up from a preceding read has to be settled first.
    """

    db.commit()
    ingest_events(_event_adapter.validate_python(payloads), db, store)


def _ensure_user(db: Session, spec: dict[str, Any]) -> None:
    if db.get(User, spec["user_id"]) is not None:
        db.commit()
        return
    db.add(User(
        user_id=spec["user_id"],
        is_synthetic=True,
        persona=spec.get("persona"),
        device_preference=spec.get("device_preference", "MOBILE"),
        lifetime_orders=int(spec.get("lifetime_orders", 0)),
        avg_order_value=float(spec.get("avg_order_value", 15_000)),
        prior_abandonment_rate=float(spec.get("prior_abandonment_rate", 0.5)),
        discount_usage_rate=float(spec.get("discount_usage_rate", 0.3)),
        return_rate=float(spec.get("return_rate", 0.08)),
        intervention_affinity={},
    ))
    db.commit()


def _envelope(
    *,
    scenario: str,
    session_id: str,
    sequence_no: int,
    spec: dict[str, Any],
    timestamp: datetime,
    user_id: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_id": deterministic_uuid(f"{scenario}:{session_id}:{sequence_no}"),
        "event_type": spec["event_type"],
        "session_id": session_id,
        "sequence_no": sequence_no,
        "client_timestamp": timestamp.isoformat(),
        "metadata": spec.get("metadata", {}),
    }
    if spec.get("product_id"):
        payload["product_id"] = spec["product_id"]
    if user_id:
        payload["user_id"] = user_id
    return payload


def replay_scenario(
    letter: str,
    db: Session,
    store: SessionStore,
    *,
    run_key: str | None = None,
    honour_arm: bool = True,
) -> dict[str, Any]:
    """Replay one scenario end to end and report expected versus actual.

    ``honour_arm`` steers session ids into the experiment arm a fixture expects,
    which is what makes scenario H a reproducible demonstration. Traffic
    simulation turns it off: forcing arms there would starve the control group
    and make the resulting uplift meaningless.
    """

    fixture = load_fixture(letter)
    scenario = fixture["scenario"]
    key = run_key or datetime.now(timezone.utc).strftime("%H%M%S%f")[:10]
    factory = sessionmaker(bind=db.get_bind(), autoflush=False, expire_on_commit=False)
    started = perf_counter()
    base_time = datetime.now(timezone.utc)
    steps: list[ReplayStep] = []

    with _immediate_decisions():
        for session in fixture["sessions"]:
            session_expect = dict(session.get("expect") or {})
            session_id = _session_id_for_arm(
                session["session_id"],
                key,
                session_expect.get("experiment_group") if honour_arm else None,
            )
            user = session.get("user")
            if isinstance(user, dict):
                _ensure_user(db, user)
            user_id = user["user_id"] if isinstance(user, dict) else None
            age = float(session.get("session_age_seconds", 180))
            sequence_no = 0
            last: dict[str, Any] | None = None

            for action in session["actions"]:
                batch: list[dict[str, Any]] = []
                for event in action.get("events", []):
                    for _ in range(int(event.get("repeat", 1))):
                        sequence_no += 1
                        timestamp = (
                            base_time - timedelta(seconds=age)
                            if event["event_type"] == "SESSION_STARTED"
                            else base_time
                        )
                        batch.append(_envelope(
                            scenario=scenario,
                            session_id=session_id,
                            sequence_no=sequence_no,
                            spec=event,
                            timestamp=timestamp,
                            user_id=user_id,
                        ))
                if batch:
                    ingest(db, store, batch)

                if "decide" in action:
                    run = run_decision(
                        session_id, action["decide"], db, store, force=True
                    )
                    db.commit()
                    if run.should_persist:
                        persist_decision(factory, run)
                    last = run.response
                    explanation = last.get("explanation") or {}
                    causes = last.get("root_causes") or []
                    recommended = last.get("recommended_intervention") or {}
                    expected = dict(action.get("expect") or {})
                    steps.append(ReplayStep(
                        session_id=session_id,
                        trigger=action["decide"],
                        decision_id=last.get("decision_id"),
                        decision=last.get("decision"),
                        intervention=recommended.get("type"),
                        dominant_cause=causes[0].get("cause") if causes else None,
                        probability=last.get("abandonment_probability"),
                        confidence=last.get("confidence_score"),
                        experiment_group=last.get("experiment_group"),
                        channel=recommended.get("channel"),
                        rendered_text=(
                            explanation.get("rendered_text")
                            if isinstance(explanation, dict) else None
                        ),
                        expected=expected,
                        mismatches=_compare(last, expected) if expected else {},
                    ))

                if action.get("dismiss_last") and last:
                    intervention = (last.get("recommended_intervention") or {}).get("type")
                    feedback: list[dict[str, Any]] = []
                    for event_type, metadata in (
                        ("INTERVENTION_SHOWN", {
                            "decision_id": last["decision_id"],
                            "intervention_id": intervention,
                            "surface": "INLINE_CARD",
                        }),
                        ("INTERVENTION_DISMISSED", {
                            "decision_id": last["decision_id"],
                            "intervention_id": intervention,
                        }),
                    ):
                        sequence_no += 1
                        feedback.append(_envelope(
                            scenario=scenario,
                            session_id=session_id,
                            sequence_no=sequence_no,
                            spec={"event_type": event_type, "metadata": metadata},
                            timestamp=base_time + timedelta(seconds=sequence_no),
                            user_id=user_id,
                        ))
                    ingest(db, store, feedback)

            if session_expect and steps:
                final = steps[-1]
                final.expected = {**session_expect, **final.expected}
                final.mismatches = _compare(last or {}, final.expected)

    intent = SCENARIO_INTENT[scenario]
    return {
        "scenario": scenario,
        "title": fixture["title"],
        "proves": intent["proves"],
        "detail": intent["detail"],
        "run_key": key,
        "passed": all(step.passed for step in steps),
        "duration_ms": round((perf_counter() - started) * 1_000, 1),
        "steps": [step.to_dict() for step in steps],
    }
