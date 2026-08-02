from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Any


class SessionStore(ABC):
    @abstractmethod
    def get(self, key: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: float, *, sliding: bool = True) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def append(self, key: str, value: Any, ttl_seconds: float, *, max_items: int = 50) -> None:
        raise NotImplementedError


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float
    hard_expires_at: float
    ttl_seconds: float
    sliding: bool


class InMemorySessionStore(SessionStore):
    """Thread-safe TTL store with a four-hour hard cap and defensive copies."""

    def __init__(self, *, hard_cap_seconds: float = 4 * 60 * 60) -> None:
        self._hard_cap_seconds = hard_cap_seconds
        self._entries: dict[str, _Entry] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        now = monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if now >= entry.expires_at or now >= entry.hard_expires_at:
                self._entries.pop(key, None)
                return None
            if entry.sliding:
                entry.expires_at = min(now + entry.ttl_seconds, entry.hard_expires_at)
            return deepcopy(entry.value)

    def set(self, key: str, value: Any, ttl_seconds: float, *, sliding: bool = True) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now = monotonic()
        with self._lock:
            current = self._entries.get(key)
            hard_expires_at = current.hard_expires_at if current else now + self._hard_cap_seconds
            self._entries[key] = _Entry(
                value=deepcopy(value),
                expires_at=min(now + ttl_seconds, hard_expires_at),
                hard_expires_at=hard_expires_at,
                ttl_seconds=ttl_seconds,
                sliding=sliding,
            )

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def append(self, key: str, value: Any, ttl_seconds: float, *, max_items: int = 50) -> None:
        if max_items <= 0:
            raise ValueError("max_items must be positive")
        current = self.get(key)
        values = current if isinstance(current, list) else []
        values.append(deepcopy(value))
        self.set(key, values[-max_items:], ttl_seconds)


class RedisSessionStore(SessionStore):
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError("RedisSessionStore is deferred; use InMemorySessionStore")

    def get(self, key: str) -> Any | None:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl_seconds: float, *, sliding: bool = True) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def append(self, key: str, value: Any, ttl_seconds: float, *, max_items: int = 50) -> None:
        raise NotImplementedError
