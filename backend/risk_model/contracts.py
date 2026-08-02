from __future__ import annotations

from dataclasses import asdict, dataclass
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

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["band"] = self.band.value
        result["top_factors"] = [asdict(item) for item in self.top_factors]
        return result


class RiskModel(Protocol):
    def predict(self, features: dict[str, float]) -> RiskPrediction: ...
