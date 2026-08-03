"""Trigger policy for the root-cause agent.

`evaluate` is pure logic over a state snapshot, so the decision is unit-testable
and identical whether it runs in a request or a test. Only `GateStore` touches
the database, and it takes a `db_path` so tests can point it at `":memory:"`.

Why gate at all: the storefront polls the model every 5 seconds. Without a gate
every poll on a risky cart would fire an LLM call — thousands per demo, blowing
through the rate limit and producing identical analyses. The gate makes the
agent run roughly **once per risk episode**.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from .. import config, db


@dataclass
class SessionState:
    """Per-session memory used for deduplication and budgeting.

    A detached read snapshot since the migration to SQLite — mutating one no
    longer writes anything back. `record_run` is the write path.
    """

    analyses_run: int = 0
    last_signature: Optional[str] = None
    last_run_at: float = 0.0


class GateStore:
    """SQLite-backed session store (`gate_state`, one row per session).

    Persisted so a backend restart doesn't hand every live session a fresh
    cooldown and a fresh analysis budget — which, on a demo where the storefront
    polls every 5 seconds, meant a restart could re-fire the LLM on every cart
    that was already diagnosed.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        # Resolved lazily so importing this module never touches the filesystem
        # and the module-level `gate_store` below stays free to construct.
        self._db_path = db_path
        self._owned: Optional[sqlite3.Connection] = None

    @property
    def _db(self) -> sqlite3.Connection:
        if self._db_path is None:
            return db.get_db()
        if self._owned is None:
            self._owned = db.get_db(self._db_path)
        return self._owned

    def get(self, session_id: str) -> SessionState:
        row = self._db.execute(
            "SELECT root_cause_signature, last_fired_at, fire_count "
            "FROM gate_state WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return SessionState()
        return SessionState(
            analyses_run=row["fire_count"],
            last_signature=row["root_cause_signature"],
            last_run_at=row["last_fired_at"],
        )

    def record_run(self, session_id: str, signature: str, at: Optional[float] = None) -> None:
        at = at if at is not None else time.time()
        connection = self._db
        with connection:
            db.touch_session(connection, session_id, at)
            connection.execute(
                """
                INSERT INTO gate_state
                    (session_id, root_cause_signature, last_fired_at, fire_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(session_id) DO UPDATE SET
                    root_cause_signature = excluded.root_cause_signature,
                    last_fired_at        = excluded.last_fired_at,
                    fire_count           = gate_state.fire_count + 1
                """,
                (session_id, signature, at),
            )

    def reset(self, session_id: Optional[str] = None) -> None:
        connection = self._db
        with connection:
            if session_id is None:
                connection.execute("DELETE FROM gate_state")
            else:
                connection.execute("DELETE FROM gate_state WHERE session_id = ?", (session_id,))


@dataclass
class GateResult:
    fired: bool
    reason: str
    threshold: float
    checks: Dict[str, object] = field(default_factory=dict)


def evaluate(
    probability: float,
    cart_age_seconds: float,
    signature: str,
    session_id: str,
    store: GateStore,
    force: bool = False,
    now: Optional[float] = None,
) -> GateResult:
    """Decide whether to spend an LLM call on this session.

    `force=True` is the manual "Re-run analysis" path: it bypasses the dedup and
    cooldown checks (which exist to save budget) but still honours the hard
    per-session cap, so a stuck UI cannot drain the quota.
    """
    now = now if now is not None else time.time()
    state = store.get(session_id)
    threshold = config.RCA_PROBABILITY_THRESHOLD

    checks: Dict[str, object] = {
        "probability": round(probability, 4),
        "threshold": threshold,
        "cart_age_seconds": round(cart_age_seconds, 1),
        "min_cart_age_seconds": config.RCA_MIN_CART_AGE_SECONDS,
        "analyses_run": state.analyses_run,
        "max_per_session": config.RCA_MAX_PER_SESSION,
        "forced": force,
    }

    # Hard budget applies even to forced runs.
    if state.analyses_run >= config.RCA_MAX_PER_SESSION:
        return GateResult(
            False,
            f"Session budget exhausted ({state.analyses_run}/{config.RCA_MAX_PER_SESSION} analyses)",
            threshold,
            checks,
        )

    if force:
        return GateResult(True, "Manually triggered (re-run requested)", threshold, checks)

    if probability < threshold:
        return GateResult(
            False,
            f"Probability {probability:.1%} is below the {threshold:.0%} high-risk threshold",
            threshold,
            checks,
        )

    if cart_age_seconds < config.RCA_MIN_CART_AGE_SECONDS:
        return GateResult(
            False,
            f"Cart is only {cart_age_seconds:.0f}s old; waiting {config.RCA_MIN_CART_AGE_SECONDS:.0f}s "
            "for signals to stabilise",
            threshold,
            checks,
        )

    seconds_since = now - state.last_run_at if state.last_run_at else None
    unchanged = state.last_signature == signature
    if unchanged and seconds_since is not None and seconds_since < config.RCA_COOLDOWN_SECONDS:
        checks["seconds_since_last_run"] = round(seconds_since, 1)
        return GateResult(
            False,
            f"Session unchanged since last analysis {seconds_since:.0f}s ago "
            f"(cooldown {config.RCA_COOLDOWN_SECONDS:.0f}s)",
            threshold,
            checks,
        )

    reason = (
        f"Probability {probability:.1%} >= {threshold:.0%}"
        + ("" if unchanged else " and session signals changed")
    )
    return GateResult(True, reason, threshold, checks)


# Module-level store used by the API.
gate_store = GateStore()
