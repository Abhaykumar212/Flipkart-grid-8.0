from __future__ import annotations

from collections.abc import Iterable

from backend.domain.causes import RootCause
from backend.domain.interventions import InterventionDefinition, InterventionId
from backend.root_cause.contracts import CauseResult

from .catalogue import INTERVENTION_CATALOGUE


def _supports(candidate: InterventionDefinition, cause: RootCause) -> bool:
    return any(supported == cause for supported in candidate.supported_causes)


def generate_candidates(
    causes: CauseResult,
    features: dict[str, float],
    catalogue: Iterable[InterventionDefinition] = INTERVENTION_CATALOGUE,
) -> tuple[InterventionDefinition, ...]:
    """Generate only governed-catalogue actions from causes and safe context."""

    entries = tuple(catalogue)
    selected = {InterventionId.NO_ACTION}
    for prediction in causes.root_causes:
        if prediction.cause == RootCause.UNKNOWN:
            continue
        selected.update(
            item.intervention_id
            for item in entries
            if item.is_active and _supports(item, prediction.cause)
        )
    if features["pay_failure_count"] > 0:
        selected.update((
            InterventionId.ALTERNATE_PAYMENT_METHOD,
            InterventionId.CHECKOUT_ASSISTANCE,
        ))
    if features["p_any_out_of_stock"] > 0:
        selected.add(InterventionId.SIMILAR_PRODUCT_RECOMMENDATION)
    if features["c_value"] >= 5_000 and features["pay_emi_eligible"] > 0:
        selected.add(InterventionId.EMI_SUGGESTION)
    return tuple(
        item for item in entries if item.is_active and item.intervention_id in selected
    )
