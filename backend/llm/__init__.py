from .base import LLMClient, LLMUnavailable, RateLimitedError
from .groq import GroqClient
from .null import NullClient


def client_from_config() -> LLMClient:
    from backend import config

    if config.LLM_PROVIDER.lower() == "null" or not config.GROQ_API_KEY:
        return NullClient()
    return GroqClient()


__all__ = ["GroqClient", "LLMClient", "LLMUnavailable", "NullClient", "RateLimitedError", "client_from_config"]
