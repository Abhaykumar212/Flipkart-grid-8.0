import pytest

from backend.domain.enums import CostLevel
from backend.feedback.affinity import affinity_for_family, beta_smoothed_ctr


def test_beta_smoothed_affinity_defaults_to_half_and_updates_per_family():
    assert beta_smoothed_ctr(0, 0) == 0.5
    rows = [("LOW", True), ("LOW", False), ("HIGH", False)]
    assert affinity_for_family(rows, CostLevel.LOW) == 0.5
    assert affinity_for_family(rows, CostLevel.HIGH) == pytest.approx(1 / 3)


def test_beta_smoothed_ctr_rejects_invalid_counts():
    with pytest.raises(ValueError):
        beta_smoothed_ctr(2, 1)

