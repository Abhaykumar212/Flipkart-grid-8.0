from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

from backend.domain.causes import RootCause


@dataclass(frozen=True, slots=True)
class CausePrediction:
    cause: RootCause
    probability: float
    evidence_keys: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["cause"] = self.cause.value
        result["evidence_keys"] = list(self.evidence_keys)
        return result


@dataclass(frozen=True, slots=True)
class CauseResult:
    root_causes: tuple[CausePrediction, ...]
    model_version: str
    abstained: bool
    confidence: float
    latency_ms: float

    @classmethod
    def unknown(
        cls,
        probability: float = 0.0,
        *,
        model_version: str = "cause-stub-v1",
        latency_ms: float = 0.0,
    ) -> "CauseResult":
        return cls(
            root_causes=(CausePrediction(RootCause.UNKNOWN, probability, ()),),
            model_version=model_version,
            abstained=True,
            confidence=probability,
            latency_ms=latency_ms,
        )

    def probability_for(self, cause: RootCause) -> float:
        return next(
            (item.probability for item in self.root_causes if item.cause == cause),
            0.0,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "root_causes": [item.to_dict() for item in self.root_causes],
            "model_version": self.model_version,
            "abstained": self.abstained,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
        }


class RootCauseModel(Protocol):
    def predict(self, features: dict[str, float]) -> CauseResult: ...
