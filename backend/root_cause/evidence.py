from backend.domain.causes import EVIDENCE_FAMILIES, RootCause


def evidence_for(cause: RootCause, shap_values: dict[str, float]) -> tuple[str, ...]:
    """Return positive per-cause SHAP evidence inside the frozen cause family."""

    candidates = [(name, shap_values.get(name, 0.0)) for name in EVIDENCE_FAMILIES[cause]]
    return tuple(name for name, _ in sorted((item for item in candidates if item[1] > 0.02), key=lambda item: (-item[1], item[0]))[:5])
