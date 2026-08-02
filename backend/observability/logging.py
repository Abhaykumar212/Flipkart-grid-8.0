from datetime import datetime, timezone
import json
import logging
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event_name", record.getMessage()),
            "trace_id": getattr(record, "trace_id", None),
            "session_id": getattr(record, "session_id", None),
        }
        payload.update(getattr(record, "structured_fields", {}))
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    trace_id: str,
    session_id: str | None,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    logger.log(
        level,
        event,
        extra={
            "event_name": event,
            "trace_id": trace_id,
            "session_id": session_id,
            "structured_fields": fields,
        },
    )
