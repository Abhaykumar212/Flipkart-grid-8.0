"""Suite-wide defaults.

The reasoning agent calls a live LLM over the network. Tests have to be
hermetic and deterministic, so the whole suite runs the trained cause-model
path; a test that wants the agent opts in by re-enabling the flag itself.

Without this the suite silently depends on a Groq key, spends real quota, and
fails differently depending on rate limits — the three properties a test suite
most needs not to have.
"""

import pytest

from backend import config
from backend.agents import reasoning


@pytest.fixture(autouse=True)
def deterministic_reasoning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "REASONING_LLM_ENABLED", False)
    reasoning.reset()
