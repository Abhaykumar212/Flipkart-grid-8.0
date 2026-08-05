"""A/B testing framework — deterministic variant assignment + aggregate readback.

The experiment: does the existing fatigue-budget delivery policy ('a', the
control — unchanged behaviour) out-convert an always-deliver policy ('b' —
`interventionPolicy.ts`'s `selectSurface` skips the fatigue/hold checks and
delivers the top-ranked lever whenever the plan is non-empty)? This is the
simplest possible experiment that actually exercises the ranked plan
differently per arm, which is what makes the comparison mean something instead
of being two labels over identical behaviour.

Assignment is a hash of the session id, not a coin flip — the same session
must land in the same arm on every request (a mid-session flip would make a
single shopper's decisions incomparable to themselves), and a hash needs no
storage to be reproducible. It is still persisted on the `sessions` row so the
frontend (which does not know how to reproduce the hash) can be told which arm
it's in via `GET /api/ab-variant/{session_id}`.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from typing import Any, Dict, Literal

from . import db

Variant = Literal["a", "b"]


def assign(session_id: str) -> Variant:
    """Pure function of the session id — stable without needing a lookup."""
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    return "a" if int(digest[:8], 16) % 2 == 0 else "b"


def get_or_assign(connection: sqlite3.Connection, session_id: str) -> Variant:
    """Read the persisted variant, assigning and storing it on first sight."""
    now = time.time()
    db.touch_session(connection, session_id, now)
    row = connection.execute(
        "SELECT ab_variant FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if row and row["ab_variant"] in ("a", "b"):
        return row["ab_variant"]  # type: ignore[return-value]

    variant = assign(session_id)
    with connection:
        connection.execute(
            "UPDATE sessions SET ab_variant = ? WHERE session_id = ?", (variant, session_id)
        )
    return variant


def summary(connection: sqlite3.Connection) -> Dict[str, Any]:
    """Aggregate accept/dismiss/conversion counts by variant, across all sessions.

    Reads `decisions.ab_variant` (stamped by `ledger.record_decision`) rather
    than joining through `sessions`, so a session whose variant assignment
    happened after some of its decisions were written still counts those
    decisions under 'unassigned' instead of silently dropping them.
    """
    rows = connection.execute(
        "SELECT ab_variant, decision_type, COUNT(*) AS n FROM decisions "
        "GROUP BY ab_variant, decision_type"
    ).fetchall()

    variants: Dict[str, Dict[str, int]] = {
        "a": {"intervene": 0, "do_nothing": 0, "elicited": 0},
        "b": {"intervene": 0, "do_nothing": 0, "elicited": 0},
    }
    for row in rows:
        variant = row["ab_variant"] if row["ab_variant"] in ("a", "b") else None
        if variant is None:
            continue
        variants[variant][row["decision_type"]] = row["n"]

    feedback_rows = connection.execute(
        """
        SELECT s.ab_variant AS variant, e.action, COUNT(*) AS n
        FROM intervention_events e
        JOIN sessions s ON s.session_id = e.session_id
        WHERE e.action IN ('accepted', 'dismissed', 'converted') AND s.ab_variant IN ('a', 'b')
        GROUP BY s.ab_variant, e.action
        """
    ).fetchall()
    feedback: Dict[str, Dict[str, int]] = {
        "a": {"accepted": 0, "dismissed": 0, "converted": 0},
        "b": {"accepted": 0, "dismissed": 0, "converted": 0},
    }
    for row in feedback_rows:
        feedback[row["variant"]][row["action"]] = row["n"]

    session_counts = connection.execute(
        "SELECT ab_variant, COUNT(*) AS n FROM sessions WHERE ab_variant IN ('a','b') GROUP BY ab_variant"
    ).fetchall()
    sessions = {"a": 0, "b": 0}
    for row in session_counts:
        sessions[row["ab_variant"]] = row["n"]

    result = {}
    for variant in ("a", "b"):
        shown = variants[variant]["intervene"] + variants[variant]["elicited"]
        held = variants[variant]["do_nothing"]
        total = shown + held
        accepted = feedback[variant]["accepted"]
        result[variant] = {
            "sessions": sessions[variant],
            "runs_intervened": shown,
            "runs_held": held,
            "runs_total": total,
            "silence_rate": round(held / total, 4) if total else 0.0,
            "accepted": accepted,
            "dismissed": feedback[variant]["dismissed"],
            "converted": feedback[variant]["converted"],
            "accept_rate": round(accepted / shown, 4) if shown else 0.0,
        }
    return {
        "label_a": "Control — fatigue-budget policy (unchanged)",
        "label_b": "Treatment — always deliver top-ranked lever",
        "variants": result,
    }


__all__ = ["assign", "get_or_assign", "summary", "Variant"]
