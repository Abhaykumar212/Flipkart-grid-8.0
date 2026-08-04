from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol

from backend.domain.enums import RiskBand


@dataclass(frozen=True, slots=True)
class RiskFactor:
    feature: str
    value: float
    shap: float


@dataclass(frozen=True, slots=True)
class RiskPrediction:
    probability: float
    confidence: float
    band: RiskBand
    model_version: str
    top_factors: tuple[RiskFactor, ...]
    latency_ms: float
    #: Signed SHAP for every risk-model feature. The agent ranks evidence inside
    #: its own diagnostic subset, so top-5 by magnitude is not enough for it.
    shap_by_feature: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["band"] = self.band.value
        result["top_factors"] = [asdict(item) for item in self.top_factors]
        # 62 extra floats on every persisted prediction row buys nothing that
        # top_factors doesn't already carry; the agent reads it off the object.
        result.pop("shap_by_feature", None)
        return result


class RiskModel(Protocol):
    def predict(self, features: dict[str, float]) -> RiskPrediction: ...
