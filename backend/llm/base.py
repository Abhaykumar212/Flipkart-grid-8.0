from __future__ import annotations

from typing import Any, Protocol


class LLMUnavailable(RuntimeError):
    """The optional language model cannot serve this request."""


class RateLimitedError(LLMUnavailable):
    """The provider refused the request because its rate limit was reached."""


class LLMClient(Protocol):
    def generate_text(self, prompt: str, max_tokens: int, timeout: float) -> str: ...

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
        timeout: float,
    ) -> dict[str, Any]: ...

