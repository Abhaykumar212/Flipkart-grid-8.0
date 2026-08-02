from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from backend.domain.causes import RootCause
from backend.feature_engine.schema import FEATURE_NAMES, RISK_MODEL_FEATURES
from ml.simulator.generate import (
    PARQUET_FILES,
    GenerationConfig,
    GenerationResult,
    generate_dataset,
)
from ml.simulator.validate import validate_data
from ml.training.build_datasets import IDENTIFIER_COLUMNS, LABEL_COLUMNS


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_small_scale_writes_all_artifacts_and_passes_ten_realism_checks(
    small_simulation: GenerationResult,
):
    data_dir = small_simulation.config.data_dir
    expected = {*PARQUET_FILES, "dataset_manifest.json"}

    assert {path.name for path in data_dir.iterdir()} == expected
    assert small_simulation.report is not None
    assert small_simulation.report.passed
    assert len(small_simulation.report.checks) == 10
    assert all(check.passed for check in validate_data(data_dir).checks)

    manifest = json.loads((data_dir / "dataset_manifest.json").read_text())
    assert manifest["counts"]["users"] == 1_200
    assert manifest["counts"]["sessions"] == 4_000
    assert manifest["feature_schema_version"] == "fs-v1"
    assert len(manifest["artifacts_sha256"]) == 6


def test_same_seed_produces_byte_identical_parquet_and_manifest(tmp_path: Path):
    directories = (tmp_path / "first", tmp_path / "second")
    for data_dir in directories:
        generate_dataset(GenerationConfig(
            seed=91,
            users=120,
            sessions=400,
            scale="test",
            data_dir=data_dir,
            validate_realism=False,
        ))

    for filename in (*PARQUET_FILES, "dataset_manifest.json"):
        assert _digest(directories[0] / filename) == _digest(directories[1] / filename)


def test_feature_matrix_has_no_latent_or_label_leakage_and_splits_are_disjoint(
    small_simulation: GenerationResult,
):
    points = pd.read_parquet(
        small_simulation.config.data_dir / "decision_points.parquet"
    )
    features = [
        column
        for column in points.columns
        if column not in {*IDENTIFIER_COLUMNS, *LABEL_COLUMNS}
    ]

    assert tuple(features) == FEATURE_NAMES
    assert "persona" not in features
    assert "cause_strength" not in features
    assert not any(column.startswith("y_") for column in features)
    assert not any(column.startswith("i_") for column in RISK_MODEL_FEATURES)

    split_users = {
        split: set(points.loc[points["split"] == split, "user_id"])
        for split in ("train", "val", "test")
    }
    assert not split_users["train"] & split_users["val"]
    assert not split_users["train"] & split_users["test"]
    assert not split_users["val"] & split_users["test"]
    ratios = points[["user_id", "split"]].drop_duplicates()["split"].value_counts(
        normalize=True
    )
    assert 0.68 <= ratios["train"] <= 0.72
    assert 0.13 <= ratios["val"] <= 0.17
    assert 0.13 <= ratios["test"] <= 0.17


def test_every_concrete_cause_has_full_scale_equivalent_support(
    small_simulation: GenerationResult,
):
    truth = pd.read_parquet(
        small_simulation.config.data_dir / "ground_truth.parquet"
    )
    counts = truth.explode("causes")["causes"].value_counts()

    for cause in RootCause:
        if cause != RootCause.UNKNOWN:
            assert counts[cause.value] >= 200


def test_forced_persona_rate_breaks_realism_check_two(
    small_simulation: GenerationResult,
):
    data_dir = small_simulation.config.data_dir
    sessions = pd.read_parquet(data_dir / "sessions.parquet")
    forced = sessions.copy()
    quality_indices = forced.index[forced["persona"] == "QUALITY_CONSCIOUS"]
    converted_count = max(1, round(len(quality_indices) * 0.05))
    forced.loc[quality_indices, "outcome"] = "ABANDONED"
    forced.loc[quality_indices[:converted_count], "outcome"] = "CONVERTED"

    from ml.simulator.validate import validate_frames

    report = validate_frames(
        events=pd.read_parquet(data_dir / "events.parquet"),
        sessions=forced,
        ground_truth=pd.read_parquet(data_dir / "ground_truth.parquet"),
        decision_points=pd.read_parquet(data_dir / "decision_points.parquet"),
        raise_on_failure=False,
    )

    assert not report.checks[1].passed
