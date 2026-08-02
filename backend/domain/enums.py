from enum import StrEnum


class RiskBand(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Decision(StrEnum):
    INTERVENE = "INTERVENE"
    NO_ACTION = "NO_ACTION"
    ABSTAIN = "ABSTAIN"


class PolicyStatus(StrEnum):
    PASS = "PASS"
    REJECT = "REJECT"
    DOWNGRADE = "DOWNGRADE"


class CostLevel(StrEnum):
    ZERO = "ZERO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Channel(StrEnum):
    INLINE_CARD = "INLINE_CARD"
    ASSISTANT_PANEL = "ASSISTANT_PANEL"
    BANNER = "BANNER"
    COMPARISON_DRAWER = "COMPARISON_DRAWER"
    CHECKOUT_PANEL = "CHECKOUT_PANEL"
