"""Execution tracing for the multi-stage pipeline.

Every stage the request passes through emits a span carrying its status,
duration and a payload the UI can expand. The frontend merges these with its own
client-side spans under a shared `pipeline_run_id` to render one continuous
waterfall.

Adding a future stage (e.g. the Phase 3 intervention agent) means adding a
member to `Stage` and wrapping the work in `span(...)` — the console needs no
changes.
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List


class Stage:
    """Pipeline stage identifiers, in execution order."""

    TELEMETRY = "telemetry"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_INFERENCE = "model_inference"
    SHAP_ATTRIBUTION = "shap_attribution"
    RISK_GATE = "risk_gate"
    ROOT_CAUSE_AGENT = "root_cause_agent"


class Status:
    OK = "ok"
    RUNNING = "running"
    SKIPPED = "skipped"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


def new_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:12]}"


class TraceRecorder:
    """Collects spans for a single pipeline run."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = run_id or new_run_id()
        self._spans: List[Dict[str, Any]] = []

    @contextmanager
    def span(self, stage: str, label: str) -> Iterator[Dict[str, Any]]:
        """Time a stage and record it.

        Yields a mutable dict; assign to `detail` inside the block to attach a
        payload. On exception the span is marked `error` and the exception is
        re-raised — tracing never swallows failures.
        """
        started_at = time.time()
        record: Dict[str, Any] = {"detail": {}, "status": Status.OK}
        try:
            yield record
        except Exception as error:
            record["status"] = Status.ERROR
            record["detail"] = {**record.get("detail", {}), "error": str(error)}
            self._append(stage, label, record, started_at)
            raise
        self._append(stage, label, record, started_at)

    def add(
        self,
        stage: str,
        label: str,
        status: str = Status.OK,
        detail: Dict[str, Any] | None = None,
        duration_ms: float = 0.0,
    ) -> None:
        """Record a span that wasn't timed — e.g. a stage that was skipped."""
        self._spans.append(
            {
                "id": f"span_{uuid.uuid4().hex[:10]}",
                "stage": stage,
                "label": label,
                "status": status,
                "started_at": time.time() * 1000.0,
                "duration_ms": round(duration_ms, 2),
                "source": "backend",
                "detail": detail or {},
            }
        )

    def _append(
        self,
        stage: str,
        label: str,
        record: Dict[str, Any],
        started_at: float,
    ) -> None:
        self._spans.append(
            {
                "id": f"span_{uuid.uuid4().hex[:10]}",
                "stage": stage,
                "label": label,
                "status": record.get("status", Status.OK),
                "started_at": started_at * 1000.0,
                "duration_ms": round((time.time() - started_at) * 1000.0, 2),
                "source": "backend",
                "detail": record.get("detail", {}),
            }
        )

    @property
    def spans(self) -> List[Dict[str, Any]]:
        return self._spans

    def total_duration_ms(self) -> float:
        return round(sum(span["duration_ms"] for span in self._spans), 2)
