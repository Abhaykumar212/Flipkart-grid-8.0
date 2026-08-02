from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from backend.domain.causes import RootCause
from backend.domain.enums import CostLevel
from backend.domain.interventions import InterventionId
from backend.recommendation.catalogue import INTERVENTION_CATALOGUE

from .causes import GroundTruth
from .state_machine import SessionRecord


FIXED_COST_RUPEES = {
    CostLevel.ZERO: 0.0,
    CostLevel.LOW: 2.0,
    CostLevel.MEDIUM: 8.0,
    CostLevel.HIGH: 25.0,
}
DISCOUNT_PCT = 0.075


def _stable_uniform(key: str) -> float:
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") / (2**64 - 1)


def counterfactual_rows(
    record: SessionRecord,
    truth: GroundTruth,
) -> list[dict[str, Any]]:
    """Return response and margin ground truth for every governed intervention."""

    if record.converted:
        return []
    strengths = json.loads(truth.to_row()["cause_strengths_json"])
    p_base = 1.0 - record.persona.base_abandonment
    session_number = int(record.session_id.rsplit("-", 1)[-1])
    fatigue_penalty = min(0.10, max(0, session_number - 1) * 0.025)
    gross_margin = record.cart_value * 0.18
    rows: list[dict[str, Any]] = []

    for definition in INTERVENTION_CATALOGUE:
        intervention = definition.intervention_id
        uplift = sum(
            record.persona.uplift.get(
                (intervention, RootCause(cause_name)), 0.0
            ) * strength
            for cause_name, strength in strengths.items()
        )
        applied_fatigue = 0.0 if intervention == InterventionId.NO_ACTION else fatigue_penalty
        p_with = float(np.clip(p_base + uplift - applied_fatigue, 0.0, 0.95))
        discount_cost = (
            record.cart_value * DISCOUNT_PCT
            if intervention == InterventionId.LIMITED_TIME_DISCOUNT
            else 0.0
        )
        fixed_cost = FIXED_COST_RUPEES[definition.cost_level]
        rows.append({
            "session_id": record.session_id,
            "user_id": record.user.user_id,
            "intervention_id": intervention.value,
            "p_convert_base": p_base,
            "p_convert_with": p_with,
            "incremental_uplift": p_with - p_base,
            "y_convert_without": 0,
            "y_convert_with": int(
                _stable_uniform(f"{record.session_id}:{intervention.value}") < p_with
            ),
            "fatigue_penalty": applied_fatigue,
            "discount_pct": (
                DISCOUNT_PCT * 100
                if intervention == InterventionId.LIMITED_TIME_DISCOUNT
                else 0.0
            ),
            "discount_cost": discount_cost,
            "gross_margin": gross_margin,
            "intervention_fixed_cost": fixed_cost,
            "estimated_margin": gross_margin - discount_cost - fixed_cost,
        })
    return rows
