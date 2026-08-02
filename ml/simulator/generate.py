from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd

from backend.feature_engine.schema import FEATURE_SCHEMA_VERSION
from ml.training.build_datasets import build_datasets

from .catalog import load_catalog
from .causes import assign_causes
from .outcomes import counterfactual_rows
from .personas import PERSONAS, PERSONA_MIX
from .state_machine import make_user_profile, simulate_session
from .validate import ValidationReport, validate_data


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SCALE_SIZES = {
    "small": (1_200, 4_000),
    "full": (12_000, 40_000),
}
PARQUET_FILES = (
    "events.parquet",
    "sessions.parquet",
    "users.parquet",
    "ground_truth.parquet",
    "decision_points.parquet",
    "counterfactuals.parquet",
)


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    seed: int = 42
    users: int = 12_000
    sessions: int = 40_000
    scale: str = "full"
    data_dir: Path = DEFAULT_DATA_DIR
    validate_realism: bool = True

    def __post_init__(self) -> None:
        if self.users < 1:
            raise ValueError("users must be positive")
        if self.sessions < self.users:
            raise ValueError("sessions must be at least users")


@dataclass(frozen=True, slots=True)
class GenerationResult:
    config: GenerationConfig
    counts: dict[str, int]
    report: ValidationReport | None
    elapsed_seconds: float


def _write_parquet(frame: pd.DataFrame, path: Path) -> None:
    frame.to_parquet(
        path,
        engine="pyarrow",
        index=False,
        compression="zstd",
        use_dictionary=False,
    )


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _session_counts(users: int, sessions: int) -> list[int]:
    quotient, remainder = divmod(sessions, users)
    return [quotient + int(index < remainder) for index in range(users)]


def _write_manifest(
    config: GenerationConfig,
    counts: dict[str, int],
    report: ValidationReport | None,
) -> None:
    artifacts = {
        name: _sha256(config.data_dir / name)
        for name in PARQUET_FILES
        if (config.data_dir / name).exists()
    }
    document: dict[str, Any] = {
        "dataset_version": "sim-v1",
        "seed": config.seed,
        "scale": config.scale,
        "users": config.users,
        "sessions": config.sessions,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "git_sha": _git_sha(),
        "counts": counts,
        "artifacts_sha256": artifacts,
    }
    if report is not None:
        document["realism_checks"] = [
            {
                "number": check.number,
                "name": check.name,
                "passed": check.passed,
                "detail": check.detail,
            }
            for check in report.checks
        ]
    (config.data_dir / "dataset_manifest.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def generate_dataset(config: GenerationConfig) -> GenerationResult:
    started = perf_counter()
    config.data_dir.mkdir(parents=True, exist_ok=True)
    products = load_catalog(seed=config.seed)
    user_streams = np.random.SeedSequence(config.seed).spawn(config.users)
    per_user_sessions = _session_counts(config.users, config.sessions)

    user_rows: list[dict[str, Any]] = []
    session_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    counterfactual_rows_all: list[dict[str, Any]] = []

    for user_index, (seed_stream, session_count) in enumerate(
        zip(user_streams, per_user_sessions, strict=True)
    ):
        rng = np.random.default_rng(seed_stream)
        persona_index = int(rng.choice(len(PERSONAS), p=PERSONA_MIX))
        persona = PERSONAS[persona_index]
        user = make_user_profile(
            user_index=user_index, persona=persona, rng=rng
        )
        user_rows.append(user.to_row())
        for session_number in range(1, session_count + 1):
            record = simulate_session(
                rng=rng,
                user=user,
                persona=persona,
                products=products,
                session_number=session_number,
                user_index=user_index,
            )
            truth = assign_causes(record, rng)
            session_rows.append(record.to_row())
            event_rows.extend(event.to_row() for event in record.events)
            truth_rows.append(truth.to_row())
            counterfactual_rows_all.extend(counterfactual_rows(record, truth))

    frames = {
        "users.parquet": pd.DataFrame(user_rows).sort_values("user_id"),
        "sessions.parquet": pd.DataFrame(session_rows).sort_values("session_id"),
        "events.parquet": pd.DataFrame(event_rows).sort_values(
            ["session_id", "sequence_no"]
        ),
        "ground_truth.parquet": pd.DataFrame(truth_rows).sort_values("session_id"),
        "counterfactuals.parquet": pd.DataFrame(counterfactual_rows_all).sort_values(
            ["session_id", "intervention_id"]
        ),
    }
    for filename, frame in frames.items():
        _write_parquet(frame.reset_index(drop=True), config.data_dir / filename)

    counts = {
        "users": len(user_rows),
        "sessions": len(session_rows),
        "events": len(event_rows),
        "ground_truth": len(truth_rows),
        "counterfactuals": len(counterfactual_rows_all),
    }
    # The preliminary manifest lets the standalone builder recover the seed if
    # generation is interrupted between raw export and feature construction.
    _write_manifest(config, counts, None)
    decision_points = build_datasets(config.data_dir, seed=config.seed)
    counts["decision_points"] = len(decision_points)
    report = validate_data(config.data_dir) if config.validate_realism else None
    _write_manifest(config, counts, report)
    return GenerationResult(
        config=config,
        counts=counts,
        report=report,
        elapsed_seconds=perf_counter() - started,
    )


def _config_from_args(args: argparse.Namespace) -> GenerationConfig:
    default_users, default_sessions = SCALE_SIZES[args.scale]
    users = args.users if args.users is not None else default_users
    sessions = args.sessions
    if sessions is None:
        sessions = (
            default_sessions
            if args.users is None
            else round(users * default_sessions / default_users)
        )
    return GenerationConfig(
        seed=args.seed,
        users=users,
        sessions=sessions,
        scale=args.scale,
        data_dir=args.output_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate causal synthetic sessions and training datasets."
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--users", type=int)
    parser.add_argument("--sessions", type=int)
    parser.add_argument("--scale", choices=tuple(SCALE_SIZES), default="full")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    result = generate_dataset(_config_from_args(args))
    assert result.report is not None
    print(result.report.format())
    print(
        f"wrote 6 parquet files + dataset_manifest.json to "
        f"{result.config.data_dir} in {result.elapsed_seconds:.2f}s"
    )
    print(
        "counts: "
        + ", ".join(f"{name}={value:,}" for name, value in result.counts.items())
    )


if __name__ == "__main__":
    main()
