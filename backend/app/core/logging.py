"""Structured logs for production: one JSON object per line, tagged with the request id.

The hosting platform keeps everything the app writes to stdout. As JSON, each line can be
searched by level, logger or request id, so a request id a user reports (shown in every
error response) leads straight to the matching server lines.

Logs never contain secrets: settings are SecretStr (masked), the database engine hides
query parameters outside development, and log messages name things rather than
printing request bodies.
"""

import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import Settings
from app.core.http_hardening import request_id_var

# Uvicorn sets up its own handlers before it loads the app; these are routed through ours.
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


class JsonFormatter(logging.Formatter):
    """Format a log record as one line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        # json.dumps escapes newlines, so nothing a client sends can forge a second log line.
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(settings: Settings) -> None:
    """Send all logs to stdout as JSON when LOG_FORMAT=json. Otherwise change nothing.

    Safe to call more than once: it replaces the root handler rather than adding another.
    """
    if settings.log_format != "json":
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)
    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
