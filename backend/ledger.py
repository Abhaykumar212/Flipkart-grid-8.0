"""Session ledger — the delivery layer's decisions, written down and read back.

The ranking pipeline decides *what* to offer; the delivery layer
(`src/context/InterventionContext.tsx`) decides whether to offer anything at all,
how loudly, and on which surface. That second decision used to exist only in the
browser's sessionStorage, so a fresh tab showed a judge an empty ledger for a
session that had actually made a dozen calls.

`record_decision` is the write path and `build_session_ledger` the read path.
Kept out of `main.py` so that file stays a list of routes, matching how the
agent logic already lives under `agents/`.

Timestamps cross the wire in **milliseconds** — the client's records are stamped
with `Date.now()`, and hydrating a mix of units into the same array would be a
quiet, hard-to-spot bug.
"""

from __future__ import annotations

import sqlite3
import time
from typing import Dict, List, Optional

from . import db
from .agents.levers import RUNG3_ASSUMED_VALUE_INR
from .schemas import (
    DeliveryDecisionRequest,
    HeldDecisionRecord,
    LedgerOutcomes,
    SessionLedgerResponse,
    SpendAvoidedEntry,
    SuppressedLeverRecord,
)

RUNG_COUNT = 4


def record_decision(
    connection: sqlite3.Connection,
    payload: DeliveryDecisionRequest,
    at: Optional[float] = None,
) -> None:
    """Persist one run's delivery decision, plus whatever it withheld.

    Written as a single transaction: a decision whose suppressed levers didn't
    land would understate the spend-avoided total, which is precisely the number
    this table exists to defend.
    """
    at = at if at is not None else time.time()
    if payload.outcome == "elicited":
        decision_type = "elicited"
    elif payload.outcome == "delivered":
        decision_type = "intervene"
    else:
        decision_type = "do_nothing"

    delivered = payload.outcome in ("delivered", "elicited")

    with connection:
        db.touch_session(connection, payload.session_id, at)
        connection.execute(
            """
            INSERT INTO decisions
                (session_id, decision_type, reason, detail, root_cause, probability, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.session_id,
                decision_type,
                payload.reason,
                payload.detail,
                payload.root_cause,
                payload.probability,
                at,
            ),
        )

        # The render event. `source='delivered'` keeps it out of the repetition
        # penalty's view (see `agents/memory.py`) while making it the one thing
        # the ledger's "shown by rung" actually counts.
        if delivered and payload.lever_id:
            connection.execute(
                """
                INSERT INTO intervention_events
                    (session_id, lever_id, intensity_rung, surface, root_cause,
                     confidence, reason, action, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'shown', 'delivered', ?)
                """,
                (
                    payload.session_id,
                    payload.lever_id,
                    payload.intensity_rung,
                    payload.surface,
                    payload.root_cause,
                    payload.confidence,
                    payload.reason,
                    at,
                ),
            )

        for lever in payload.suppressed:
            connection.execute(
                """
                INSERT INTO intervention_events
                    (session_id, lever_id, intensity_rung, root_cause, reason,
                     action, source, created_at)
                VALUES (?, ?, 3, ?, ?, 'suppressed', 'suppressed', ?)
                """,
                (payload.session_id, lever.lever_id, payload.root_cause, lever.reason, at),
            )


def record_critic_rejection(
    connection: sqlite3.Connection,
    session_id: str,
    lever_id: str,
    reason: str,
    root_cause: Optional[str] = None,
    at: Optional[float] = None,
) -> None:
    """A lever the critic refused, written as considered-and-withheld.

    `source='suppressed'` keeps it out of `shownByRung` (which counts
    `'delivered'` only) and out of the repetition penalty (which reads
    `'ranked'`), so a rejection costs the lever nothing but a record.

    `intensity_rung` stays NULL, unlike the rung-3 policy suppressions
    `record_decision` writes: those are margin-spending levers whose assumed
    value the ledger totals, and this rejection is about alignment, not spend.
    `build_session_ledger` uses that NULL to tell the two apart.
    """
    at = at if at is not None else time.time()
    with connection:
        db.touch_session(connection, session_id, at)
        connection.execute(
            """
            INSERT INTO intervention_events
                (session_id, lever_id, root_cause, reason, action, source, created_at)
            VALUES (?, ?, ?, ?, 'suppressed', 'suppressed', ?)
            """,
            (session_id, lever_id, root_cause, reason, at),
        )


def annotate_latest_event(
    connection: sqlite3.Connection,
    session_id: str,
    lever_id: str,
    action: str,
    intensity_rung: Optional[int] = None,
    surface: Optional[str] = None,
    root_cause: Optional[str] = None,
    confidence: Optional[str] = None,
    explanation_verdict: Optional[str] = None,
) -> None:
    """Attach delivery context to the feedback row `memory_store` just wrote.

    `InterventionMemoryStore.record` keeps the narrow signature every existing
    call site uses; this fills in the columns the ledger wants without widening
    it. `COALESCE` so a client that sends nothing never blanks a populated field.
    """
    if (
        intensity_rung is None
        and surface is None
        and root_cause is None
        and confidence is None
        and explanation_verdict is None
    ):
        return
    with connection:
        connection.execute(
            """
            UPDATE intervention_events
               SET intensity_rung      = COALESCE(?, intensity_rung),
                   surface             = COALESCE(?, surface),
                   root_cause          = COALESCE(?, root_cause),
                   confidence          = COALESCE(?, confidence),
                   explanation_verdict = COALESCE(?, explanation_verdict)
             WHERE id = (
                 SELECT id FROM intervention_events
                  WHERE session_id = ? AND lever_id = ? AND action = ?
                  ORDER BY id DESC LIMIT 1
             )
            """,
            (
                intensity_rung,
                surface,
                root_cause,
                confidence,
                explanation_verdict,
                session_id,
                lever_id,
                action,
            ),
        )


def _ms(seconds: float) -> float:
    return round(seconds * 1000.0)


def build_session_ledger(
    connection: sqlite3.Connection, session_id: str
) -> SessionLedgerResponse:
    """Aggregate one session into the shape `InterventionLedgerPanel` renders."""
    shown_by_rung = [0] * RUNG_COUNT
    shown_per_lever: Dict[str, int] = {}

    delivered_rows = connection.execute(
        "SELECT lever_id, intensity_rung FROM intervention_events "
        "WHERE session_id = ? AND source = 'delivered' AND action = 'shown'",
        (session_id,),
    ).fetchall()
    for row in delivered_rows:
        rung = row["intensity_rung"]
        if rung is not None and 0 <= rung < RUNG_COUNT:
            shown_by_rung[rung] += 1
        shown_per_lever[row["lever_id"]] = shown_per_lever.get(row["lever_id"], 0) + 1

    responses = connection.execute(
        "SELECT lever_id, action, COUNT(*) AS n FROM intervention_events "
        "WHERE session_id = ? AND action IN ('accepted', 'dismissed') "
        "GROUP BY lever_id, action",
        (session_id,),
    ).fetchall()
    resolved_per_lever: Dict[str, int] = {}
    accepted = 0
    dismissed = 0
    for row in responses:
        resolved_per_lever[row["lever_id"]] = resolved_per_lever.get(row["lever_id"], 0) + row["n"]
        if row["action"] == "accepted":
            accepted += row["n"]
        else:
            dismissed += row["n"]

    # "Ignored" mirrors the panel's `outcome === "pending"`: an exposure that was
    # rendered and never answered. Clamped at zero because feedback can in
    # principle arrive for a lever whose render event was never recorded (the
    # companion widget has its own accept/dismiss path).
    ignored = sum(
        max(0, count - resolved_per_lever.get(lever_id, 0))
        for lever_id, count in shown_per_lever.items()
    )

    held_rows = connection.execute(
        "SELECT reason, detail, root_cause, created_at FROM decisions "
        "WHERE session_id = ? AND decision_type = 'do_nothing' ORDER BY id",
        (session_id,),
    ).fetchall()
    held: List[HeldDecisionRecord] = []
    held_by_reason: Dict[str, int] = {}
    for row in held_rows:
        held.append(
            HeldDecisionRecord(
                reason=row["reason"],
                rootCause=row["root_cause"],
                detail=row["detail"],
                at=_ms(row["created_at"]),
            )
        )
        if row["reason"]:
            held_by_reason[row["reason"]] = held_by_reason.get(row["reason"], 0) + 1

    # Rung 3 specifically, not every suppression. `record_critic_rejection`
    # writes a NULL rung, and folding those in would add spend-avoided rupees
    # the client's sessionStorage copy knows nothing about — so the panel's
    # total would jump the moment it rehydrated from the server.
    suppressed_rows = connection.execute(
        "SELECT lever_id, reason, created_at FROM intervention_events "
        "WHERE session_id = ? AND source = 'suppressed' AND intensity_rung = 3 ORDER BY id",
        (session_id,),
    ).fetchall()
    suppressed: List[SuppressedLeverRecord] = []
    spend_by_lever: Dict[str, SpendAvoidedEntry] = {}
    for row in suppressed_rows:
        lever_id = row["lever_id"]
        suppressed.append(
            SuppressedLeverRecord(
                leverId=lever_id, reason=row["reason"] or "", at=_ms(row["created_at"])
            )
        )
        unit = RUNG3_ASSUMED_VALUE_INR.get(lever_id, 0)
        entry = spend_by_lever.get(lever_id)
        if entry is None:
            spend_by_lever[lever_id] = SpendAvoidedEntry(
                count=1, assumedUnitValueInr=unit, totalInr=unit
            )
        else:
            entry.count += 1
            entry.totalInr += unit

    # How often this session chose to stay quiet. Both verdicts are already in
    # `decisions` — a run that intervened and a run that held are equally
    # recorded — so this is arithmetic over rows, not new bookkeeping.
    verdicts = connection.execute(
        "SELECT decision_type, COUNT(*) AS n FROM decisions WHERE session_id = ? "
        "GROUP BY decision_type",
        (session_id,),
    ).fetchall()
    counts = {row["decision_type"]: row["n"] for row in verdicts}
    held_count = counts.get("do_nothing", 0)
    inferred_count = counts.get("intervene", 0)
    elicitation_count = counts.get("elicited", 0)
    total_decisions = held_count + inferred_count + elicitation_count

    return SessionLedgerResponse(
        session_id=session_id,
        shownByRung=shown_by_rung,
        silenceRate=round(held_count / total_decisions, 4) if total_decisions else 0.0,
        outcomes=LedgerOutcomes(accepted=accepted, dismissed=dismissed, ignored=ignored),
        held=held,
        heldByReason=held_by_reason,
        suppressedRung3=suppressed,
        spendAvoidedInr=sum(entry.totalInr for entry in spend_by_lever.values()),
        spendAvoidedByLever=spend_by_lever,
        elicitation_count=elicitation_count,
        inferred_count=inferred_count,
    )
