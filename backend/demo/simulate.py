"""Synthetic traffic that exercises the whole loop, outcomes included.

An A/B panel reading all zeros tells a reviewer nothing about whether the
experiment machinery works. This drives real sessions through the real pipeline
and then plays a *documented* shopper-response model against whatever the agent
decided, so the uplift figures on the dashboard are measured from behaviour
rather than written down.

The response model is an explicit assumption, not a result. It is returned with
every run and surfaced in the UI so nobody mistakes simulated shoppers for
production evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import random
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.storage.session_store import SessionStore

from .replay import deterministic_uuid, ingest, replay_scenario

#: Scenarios worth sampling for traffic. G is excluded because it depends on a
#: pre-existing fatigue history that only makes sense as a standalone proof.
TRAFFIC_MIX: tuple[tuple[str, int], ...] = (
    ("A", 3), ("B", 2), ("C", 2), ("D", 2), ("E", 3), ("F", 1), ("H", 3),
)


@dataclass(frozen=True, slots=True)
class ResponseModel:
    """How a simulated shopper reacts to what the agent decided.

    Each shopper's baseline is the model's own calibrated abandonment
    probability, so a session the agent correctly left alone still converts at
    the rate that session deserved. Interventions move that baseline, and the
    only asymmetry is ``matched_click``/``matched_lift``: a nudge that addresses
    the diagnosed reason for hesitation is assumed to land more often, and to
    help more when it lands, than a generic one.

    That asymmetry is the hypothesis the experiment exists to test. It is stated
    here rather than buried in the arithmetic, and it is the only place the
    simulation prefers one arm over the other.
    """

    matched_click: float = 0.44
    generic_click: float = 0.19
    matched_lift: float = 0.20
    generic_lift: float = 0.06
    seen_but_ignored_lift: float = 0.02
    #: An irrelevant nudge gets swatted away far more often than a useful one.
    matched_dismissal: float = 0.18
    generic_dismissal: float = 0.45
    #: Being nudged and dismissing it leaves the shopper worse than being left
    #: alone. Without this cost, blanket nudging would always look free, which
    #: is precisely the over-serving trap the policy engine exists to avoid.
    dismissal_penalty: float = 0.06
    min_conversion: float = 0.02
    max_conversion: float = 0.95

    def click_rate(self, *, matched: bool) -> float:
        return self.matched_click if matched else self.generic_click

    def dismissal_rate(self, *, matched: bool) -> float:
        return self.matched_dismissal if matched else self.generic_dismissal

    def conversion_rate(
        self,
        *,
        abandonment_probability: float,
        shown: bool,
        clicked: bool,
        dismissed: bool,
        matched: bool,
    ) -> float:
        """Convert a calibrated risk plus an intervention outcome into a rate."""

        rate = 1.0 - max(0.0, min(1.0, abandonment_probability))
        if shown:
            if clicked:
                rate += self.matched_lift if matched else self.generic_lift
            elif dismissed:
                rate -= self.dismissal_penalty
            else:
                rate += self.seen_but_ignored_lift
        return max(self.min_conversion, min(self.max_conversion, rate))

    def to_dict(self) -> dict[str, float | str]:
        return {
            "baseline": "1 - calibrated abandonment probability for that session",
            "matched_click": self.matched_click,
            "generic_click": self.generic_click,
            "matched_lift": self.matched_lift,
            "generic_lift": self.generic_lift,
            "seen_but_ignored_lift": self.seen_but_ignored_lift,
            "matched_dismissal": self.matched_dismissal,
            "generic_dismissal": self.generic_dismissal,
            "dismissal_penalty": self.dismissal_penalty,
        }


RESPONSE_MODEL = ResponseModel()

#: Interventions that directly answer a diagnosed cause. Anything outside this
#: mapping is treated as a generic nudge by the response model.
CAUSE_MATCHED: dict[str, set[str]] = {
    "PRODUCT_QUALITY_UNCERTAINTY": {"REVIEW_SUMMARY", "PRODUCT_COMPARISON"},
    "DELIVERY_CONCERN": {"DELIVERY_REASSURANCE"},
    "PRICE_SENSITIVITY": {"PRICE_DROP_ALERT", "LIMITED_TIME_DISCOUNT"},
    "CHECKOUT_OR_PAYMENT_FAILURE": {"ALTERNATE_PAYMENT_METHOD", "CHECKOUT_ASSISTANCE"},
    "AFFORDABILITY_OR_EMI_NEED": {"EMI_SUGGESTION"},
    "CHOICE_OVERLOAD": {"PRODUCT_COMPARISON", "SIMILAR_PRODUCT_RECOMMENDATION"},
    "TRUST_OR_RETURN_POLICY_CONCERN": {"RETURN_POLICY_REASSURANCE"},
    "PRODUCT_AVAILABILITY_CONCERN": {"SIMILAR_PRODUCT_RECOMMENDATION"},
    "LOW_PURCHASE_INTENT": {"WISHLIST_REMINDER"},
    "SESSION_INTERRUPTION_OR_DISTRACTION": {"WISHLIST_REMINDER"},
}


def _emit(
    db: Session,
    store: SessionStore,
    session_id: str,
    specs: list[dict[str, Any]],
    *,
    start_sequence: int,
    slot: str,
) -> None:
    """Append outcome events for one decision.

    ``slot`` keys the event ids. A session can receive several decisions, and
    without it every decision's outcome tail would mint the same identifiers and
    be silently rejected as duplicates by the idempotent ingest path.
    """

    base = datetime.now(timezone.utc)
    payloads = [
        {
            "event_id": deterministic_uuid(f"sim:{session_id}:{slot}:{start_sequence + index}"),
            "event_type": spec["event_type"],
            "session_id": session_id,
            "sequence_no": start_sequence + index,
            "client_timestamp": (base + timedelta(seconds=index + 1)).isoformat(),
            "metadata": spec["metadata"],
        }
        for index, spec in enumerate(specs)
    ]
    ingest(db, store, payloads)


def _play_outcome(
    db: Session,
    store: SessionStore,
    step: dict[str, Any],
    rng: random.Random,
    model: ResponseModel,
    slot: int,
) -> dict[str, int]:
    """Play one simulated shopper's response to a single decision."""

    tally = {"shown": 0, "clicked": 0, "dismissed": 0, "converted": 0}
    session_id = step["session_id"]
    intervention = step.get("intervention")
    intervened = bool(step.get("decision") == "INTERVENE" and intervention)
    # The control arm applies one fixed reminder whatever the diagnosis, so it
    # is generic by construction even when its label happens to line up.
    matched = (
        step.get("experiment_group") != "CONTROL"
        and intervention in CAUSE_MATCHED.get(step.get("dominant_cause") or "", set())
    )

    specs: list[dict[str, Any]] = []
    clicked = False
    if intervened:
        specs.append({
            "event_type": "INTERVENTION_SHOWN",
            "metadata": {
                "decision_id": step["decision_id"],
                "intervention_id": intervention,
                "surface": step.get("channel") or "INLINE_CARD",
            },
        })
        tally["shown"] = 1
        clicked = rng.random() < model.click_rate(matched=matched)
        if clicked:
            specs.append({
                "event_type": "INTERVENTION_CLICKED",
                "metadata": {
                    "decision_id": step["decision_id"],
                    "intervention_id": intervention,
                },
            })
            tally["clicked"] = 1
        elif rng.random() < model.dismissal_rate(matched=matched):
            specs.append({
                "event_type": "INTERVENTION_DISMISSED",
                "metadata": {
                    "decision_id": step["decision_id"],
                    "intervention_id": intervention,
                },
            })
            tally["dismissed"] = 1

    convert_rate = model.conversion_rate(
        abandonment_probability=float(step.get("probability") or 0.5),
        shown=intervened,
        clicked=clicked,
        dismissed=bool(tally["dismissed"]),
        matched=matched,
    )
    if rng.random() < convert_rate:
        specs.append({
            "event_type": "ORDER_COMPLETED",
            "metadata": {
                "order_id": f"O-{uuid4().hex[:12]}",
                "order_value": round(rng.uniform(1_200, 92_000), 2),
                "payment_method": rng.choice(["UPI", "CARD", "COD", "NETBANKING"]),
            },
        })
        tally["converted"] = 1
    else:
        specs.append({
            "event_type": "SESSION_ENDED",
            "metadata": {"reason": rng.choice(["TIMEOUT", "UNLOAD"])},
        })

    if specs:
        # Fixture replays never exceed a few dozen events, so starting the
        # outcome tail well above that keeps sequence numbers monotonic.
        _emit(
            db,
            store,
            session_id,
            specs,
            start_sequence=900 + slot * 10,
            slot=str(step.get("decision_id") or slot),
        )
    return tally


def simulate_traffic(
    db: Session,
    store: SessionStore,
    *,
    sessions: int = 24,
    seed: int | None = None,
) -> dict[str, Any]:
    """Drive ``sessions`` synthetic shoppers through the full loop."""

    rng = random.Random(seed if seed is not None else 20260803)
    key_prefix = f"sim{rng.randrange(16**6):06x}"
    weighted = [letter for letter, weight in TRAFFIC_MIX for _ in range(weight)]
    totals = {"sessions": 0, "decisions": 0, "shown": 0, "clicked": 0, "dismissed": 0, "converted": 0}
    by_scenario: dict[str, int] = {}

    for index in range(sessions):
        letter = rng.choice(weighted)
        result = replay_scenario(
            letter, db, store, run_key=f"{key_prefix}-{index}", honour_arm=False
        )
        by_scenario[letter] = by_scenario.get(letter, 0) + 1
        totals["sessions"] += 1
        for slot, step in enumerate(result["steps"]):
            totals["decisions"] += 1
            tally = _play_outcome(db, store, step, rng, RESPONSE_MODEL, slot)
            for name, value in tally.items():
                totals[name] += value

    return {
        "requested_sessions": sessions,
        "totals": totals,
        "by_scenario": dict(sorted(by_scenario.items())),
        "response_model": RESPONSE_MODEL.to_dict(),
        "disclaimer": (
            "Simulated shoppers responding to real pipeline decisions. Uplift is measured "
            "from these responses and is not production evidence."
        ),
    }
