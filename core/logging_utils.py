import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone


class StructuredJsonFormatter(logging.Formatter):
    """Formatter that emits JSON for easy ingestion in ELK/CloudWatch."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting utility
        base = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key
            not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }
        }

        if record.exc_info:
            extras["exception"] = self.formatException(record.exc_info)

        payload = {**base, **extras}
        return json.dumps(payload, default=str)


class CollectorHTTPHandler(logging.Handler):
    """Sends structured logs to an external collector via HTTP POST."""

    def __init__(self, endpoint: str, token: str | None = None, timeout: int = 2):
        super().__init__()
        self.endpoint = endpoint
        self.token = token
        self.timeout = timeout

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - network side-effect
        try:
            body = self.format(record).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            request = urllib.request.Request(
                self.endpoint, data=body, headers=headers, method="POST"
            )
            with urllib.request.urlopen(request, timeout=self.timeout):
                pass
        except Exception:
            self.handleError(record)
