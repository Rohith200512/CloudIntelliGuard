"""Structured JSON logging for CloudIntelliGuard. Never log passwords or secrets."""
import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Format log records as newline-delimited JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def setup_logging() -> logging.Logger:
    """Configure and return the root application logger."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger = logging.getLogger("cig")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    return logger


logger = setup_logging()


def log_audit(
    action: str,
    user_id: Optional[int] = None,
    resource: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a structured audit log entry. NEVER pass passwords or secrets."""
    logger.info(
        json.dumps(
            {
                "audit": True,
                "action": action,
                "user_id": user_id,
                "resource": resource,
                "detail": detail or {},
            }
        )
    )
