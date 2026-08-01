"""Trigger policy for the root-cause agent.

Pure logic, no I/O, so the decision is unit-testable and identical whether it
runs in a request or a test.

Why gate at all: the storefront polls the model every 5 seconds. Without a gate
every poll on a risky cart would fire an LLM call — thousands per demo, blowing
through the rate limit and producing identical analyses. The gate makes the
agent run roughly **once per risk episode**.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from .. import config


@dataclass
class SessionState:
    """Per-session memory used for deduplication and budgeting."""

    analyses_run: int = 0
    last_signature: Optional[str] = None
    last_run_at: float = 0.0


class GateStore:
    """In-memory session store.

    Process-local by design: this is a demo service with a single backend
    instance. A production deployment would back this with Redis so the state
    survives restarts and is shared across replicas.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        return self._sessions.setdefault(session_id, SessionState())

    def record_run(self, session_id: str, signature: str, at: Optional[float] = None) -> None:
        state = self.get(session_id)
        state.analyses_run += 1
        state.last_signature = signature
        state.last_run_at = at if at is not None else time.time()

    def reset(self, session_id: Optional[str] = None) -> None:
        if session_id is None:
            self._sessions.clear()
        else:
            self._sessions.pop(session_id, None)


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
