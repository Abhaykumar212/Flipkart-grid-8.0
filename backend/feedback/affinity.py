from __future__ import annotations

from collections.abc import Iterable

from backend.domain.enums import CostLevel


def beta_smoothed_ctr(clicks: int, impressions: int) -> float:
    """Return the Beta(1, 1) posterior mean for a click-through rate."""

    if clicks < 0 or impressions < 0 or clicks > impressions:
        raise ValueError("clicks and impressions must satisfy 0 <= clicks <= impressions")
    return (clicks + 1) / (impressions + 2)


def affinity_for_family(
    observations: Iterable[tuple[str, bool]],
    cost_level: CostLevel,
) -> float:
    """Compute per-user affinity for an informational or incentive family."""

    clicked = [was_clicked for family, was_clicked in observations if family == cost_level.value]
    return beta_smoothed_ctr(sum(clicked), len(clicked))

