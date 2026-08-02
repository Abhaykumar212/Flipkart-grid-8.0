from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

from backend.domain.causes import RootCause

from .personas import PERSONA_BY_NAME


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
FULL_SCALE_SESSIONS = 40_000
FULL_SCALE_MIN_CAUSE_COUNT = 2_000


@dataclass(frozen=True, slots=True)
class CheckResult:
    number: int
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    checks: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def format(self) -> str:
        return "\n".join(
            f"{check.number:02d} {'PASS' if check.passed else 'FAIL'} "
            f"{check.name}: {check.detail}"
            for check in self.checks
        )


class RealismValidationError(RuntimeError):
    def __init__(self, report: ValidationReport) -> None:
        super().__init__("simulator realism checks failed\n" + report.format())
        self.report = report


def _result(number: int, name: str, passed: bool, detail: str) -> CheckResult:
    return CheckResult(number, name, bool(passed), detail)


def _cause_values(value: object) -> list[str]:
    if isinstance(value, np.ndarray):
        return [str(item) for item in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return []


def validate_frames(
    *,
    events: pd.DataFrame,
    sessions: pd.DataFrame,
    ground_truth: pd.DataFrame,
    decision_points: pd.DataFrame,
    raise_on_failure: bool = True,
) -> ValidationReport:
    checks: list[CheckResult] = []

    overall_rate = float((sessions["outcome"] == "ABANDONED").mean())
    checks.append(_result(
        1,
        "overall abandonment",
        0.62 <= overall_rate <= 0.74,
        f"rate={overall_rate:.4f}, expected [0.62, 0.74]",
    ))

    realized = sessions.assign(
        abandoned=(sessions["outcome"] == "ABANDONED").astype(float)
    ).groupby("persona")["abandoned"].mean()
    deviations = {
        persona_name: abs(
            float(realized.get(persona_name, float("nan")))
            - persona.base_abandonment
        )
        for persona_name, persona in PERSONA_BY_NAME.items()
    }
    persona_rates_ok = all(np.isfinite(value) and value <= 0.06 for value in deviations.values())
    checks.append(_result(
        2,
        "persona abandonment calibration",
        persona_rates_ok,
        "max deviation="
        f"{max(deviations.values()):.4f}; "
        + ", ".join(
            f"{name.value}={realized.get(name.value, float('nan')):.3f}"
            for name in PERSONA_BY_NAME
        ),
    ))

    exploded = ground_truth.assign(
        causes=ground_truth["causes"].map(_cause_values)
    ).explode("causes")
    cause_counts = exploded["causes"].value_counts().to_dict()
    concrete_causes = [cause.value for cause in RootCause if cause != RootCause.UNKNOWN]
    scaled_minimum = max(
        20,
        round(FULL_SCALE_MIN_CAUSE_COUNT * len(sessions) / FULL_SCALE_SESSIONS),
    )
    minimum_observed = min(int(cause_counts.get(cause, 0)) for cause in concrete_causes)
    checks.append(_result(
        3,
        "cause support",
        minimum_observed >= scaled_minimum,
        f"minimum={minimum_observed}, required={scaled_minimum} "
        f"({FULL_SCALE_MIN_CAUSE_COUNT} at full scale)",
    ))

    lengths = events.groupby("session_id", sort=False).size()
    median_length = float(lengths.median())
    checks.append(_result(
        4,
        "session event length",
        8 <= median_length <= 60,
        f"median={median_length:.1f}, expected [8, 60]",
    ))

    per_session = decision_points.groupby("session_id", as_index=False).agg({
        "s_review_open_count": "max",
        "d_check_count": "max",
        "pay_failure_count": "max",
    }).merge(sessions[["session_id", "persona"]], on="session_id", how="left")

    def signature_check(
        number: int,
        persona: str,
        column: str,
        multiplier: float,
        label: str,
    ) -> CheckResult:
        population_mean = float(per_session[column].mean())
        persona_mean = float(
            per_session.loc[per_session["persona"] == persona, column].mean()
        )
        return _result(
            number,
            label,
            persona_mean > multiplier * population_mean,
            f"persona={persona_mean:.3f}, population={population_mean:.3f}, "
            f"ratio={persona_mean / max(population_mean, 1e-12):.2f}",
        )

    checks.append(signature_check(
        5,
        "QUALITY_CONSCIOUS",
        "s_review_open_count",
        2.0,
        "quality review signature",
    ))
    checks.append(signature_check(
        6,
        "URGENT_DELIVERY",
        "d_check_count",
        2.0,
        "delivery-check signature",
    ))
    checks.append(signature_check(
        7,
        "PAYMENT_CONSTRAINED",
        "pay_failure_count",
        3.0,
        "payment-failure signature",
    ))

    order_not_terminal: list[str] = []
    invalid_sequences: list[str] = []
    for session_id, group in events.groupby("session_id", sort=False):
        ordered = group.sort_values("sequence_no")
        event_types = ordered["event_type"].tolist()
        if "ORDER_COMPLETED" in event_types and event_types[-1] != "ORDER_COMPLETED":
            order_not_terminal.append(str(session_id))
        sequence = ordered["sequence_no"].astype(int).to_numpy()
        if len(sequence) and not np.array_equal(sequence, np.arange(1, len(sequence) + 1)):
            invalid_sequences.append(str(session_id))
    checks.append(_result(
        8,
        "ORDER_COMPLETED is terminal",
        not order_not_terminal,
        f"violations={len(order_not_terminal)}",
    ))
    checks.append(_result(
        9,
        "gapless increasing sequence numbers",
        not invalid_sequences,
        f"violations={len(invalid_sequences)}",
    ))

    cause_sets = ground_truth.set_index("session_id")["causes"].map(_cause_values)
    indicators = pd.DataFrame(
        {
            cause: cause_sets.map(lambda values, name=cause: int(name in values))
            for cause in concrete_causes
        }
    )
    correlation = indicators.corr().abs()
    upper = correlation.where(np.triu(np.ones(correlation.shape), k=1).astype(bool))
    max_correlation = float(upper.max().max())
    checks.append(_result(
        10,
        "cause separability",
        np.isfinite(max_correlation) and max_correlation <= 0.95,
        f"maximum |r|={max_correlation:.4f}",
    ))

    report = ValidationReport(tuple(checks))
    if raise_on_failure and not report.passed:
        raise RealismValidationError(report)
    return report


def validate_data(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    *,
    raise_on_failure: bool = True,
) -> ValidationReport:
    data_path = Path(data_dir)

    def loader(name: str) -> pd.DataFrame:
        return pd.read_parquet(data_path / name)

    return validate_frames(
        events=loader("events.parquet"),
        sessions=loader("sessions.parquet"),
        ground_truth=loader("ground_truth.parquet"),
        decision_points=loader("decision_points.parquet"),
        raise_on_failure=raise_on_failure,
    )
