from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import numpy as np
from numpy.random import Generator

from backend.domain.causes import RootCause

from .state_machine import SessionRecord


@dataclass(frozen=True, slots=True)
class GroundTruth:
    session_id: str
    user_id: str
    persona: str
    causes: tuple[str, ...]
    cause_strengths: dict[str, float]

    def to_row(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "persona": self.persona,
            "causes": list(self.causes),
            "cause_strengths_json": json.dumps(
                self.cause_strengths, sort_keys=True, separators=(",", ":")
            ),
        }


def _activate(
    active: dict[RootCause, float], cause: RootCause, probability: float, rng: Generator
) -> None:
    if rng.random() < probability:
        active[cause] = float(np.clip(rng.normal(probability, 0.08), 0.4, 1.0))


def assign_causes(record: SessionRecord, rng: Generator) -> GroundTruth:
    """Draw latent causes separately from the observable event stream."""

    active: dict[RootCause, float] = {}
    for cause, probability in record.persona.causes.items():
        if probability >= 0.40:
            _activate(active, cause, probability, rng)

    facts = record.primary_product.facts
    if not facts.in_stock or facts.quantity_left <= 5:
        _activate(active, RootCause.PRODUCT_AVAILABILITY_CONCERN, 0.55, rng)
    if record.primary_product.seller_rating < 4.0 or record.user.return_rate > 0.25:
        _activate(active, RootCause.TRUST_OR_RETURN_POLICY_CONCERN, 0.45, rng)

    if not record.converted and not active:
        if record.persona.causes:
            cause, probability = max(
                record.persona.causes.items(), key=lambda item: item[1]
            )
            active[cause] = probability
        else:
            event_types = {event.event_type for event in record.events}
            fallback = (
                RootCause.CHECKOUT_OR_PAYMENT_FAILURE
                if "PAYMENT_FAILED" in event_types
                else RootCause.SESSION_INTERRUPTION_OR_DISTRACTION
            )
            active[fallback] = 0.45

    ordered = tuple(sorted((cause.value for cause in active)))
    strengths = {cause.value: active[cause] for cause in sorted(active, key=str)}
    return GroundTruth(
        session_id=record.session_id,
        user_id=record.user.user_id,
        persona=record.persona.name.value,
        causes=ordered,
        cause_strengths=strengths,
    )
