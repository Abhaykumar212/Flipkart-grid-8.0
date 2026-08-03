from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import RLock
from time import monotonic


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowRateLimiter:
    def __init__(self, *, window_seconds: float = 60.0) -> None:
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()

    def acquire(
        self,
        key: str,
        *,
        limit: int,
        amount: int = 1,
        now: float | None = None,
    ) -> RateLimitResult:
        observed_at = monotonic() if now is None else now
        cutoff = observed_at - self.window_seconds
        with self._lock:
            requests = self._requests[key]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) + amount > limit:
                retry = max(1, int(self.window_seconds - (observed_at - requests[0])) + 1)
                return RateLimitResult(False, retry)
            requests.extend([observed_at] * amount)
            return RateLimitResult(True)

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


event_rate_limiter = SlidingWindowRateLimiter()
decision_rate_limiter = SlidingWindowRateLimiter()
