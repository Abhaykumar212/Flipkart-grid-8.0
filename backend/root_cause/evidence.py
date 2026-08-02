from backend.domain.causes import EVIDENCE_FAMILIES, RootCause


def evidence_for(cause: RootCause, features: dict[str, float]) -> tuple[str, ...]:
    """Attach only present behavioral evidence from the frozen cause family."""

    keys = []
    for name in EVIDENCE_FAMILIES[cause]:
        value = features.get(name, 0.0)
        if name == "p_avg_rating":
            present = value < 4.2
        elif name == "u_avg_order_value":
            present = features.get("c_value_to_aov_ratio", 0.0) > 1
        else:
            present = abs(value) > 0
        if present:
            keys.append(name)
    return tuple(keys)
