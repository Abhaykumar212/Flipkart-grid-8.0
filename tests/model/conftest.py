from pathlib import Path

import pytest

from ml.simulator.generate import GenerationConfig, GenerationResult, generate_dataset


@pytest.fixture(scope="session")
def small_simulation(tmp_path_factory: pytest.TempPathFactory) -> GenerationResult:
    data_dir: Path = tmp_path_factory.mktemp("simulator-small")
    return generate_dataset(GenerationConfig(
        seed=42,
        users=1_200,
        sessions=4_000,
        scale="small",
        data_dir=data_dir,
    ))
