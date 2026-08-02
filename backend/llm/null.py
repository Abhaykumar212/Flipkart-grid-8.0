from __future__ import annotations

from typing import Any

from .base import LLMUnavailable


class NullClient:
    def generate_text(self, prompt: str, max_tokens: int, timeout: float) -> str:
        del prompt, max_tokens, timeout
        raise LLMUnavailable("LLM rendering is disabled")

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
        timeout: float,
    ) -> dict[str, Any]:
        del prompt, schema, max_tokens, timeout
        raise LLMUnavailable("LLM rendering is disabled")

