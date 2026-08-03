from backend.domain.causes import EVIDENCE_FAMILIES, RootCause
from backend.root_cause.evidence import evidence_for


def test_evidence_is_nonempty_and_never_escapes_the_cause_family() -> None:
    for cause in RootCause:
        if cause is RootCause.UNKNOWN:
            continue
        family = EVIDENCE_FAMILIES[cause]
        shap_values = {name: 0.10 + index / 100 for index, name in enumerate(family)}
        selected = evidence_for(cause, shap_values)
        assert selected
        assert set(selected) <= set(family)


def test_non_positive_or_tiny_shap_values_are_not_presented_as_evidence() -> None:
    cause = RootCause.CHECKOUT_OR_PAYMENT_FAILURE
    values = {name: 0.02 for name in EVIDENCE_FAMILIES[cause]}
    assert evidence_for(cause, values) == ()
