import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

try:  # pragma: no cover
    from opentelemetry import trace
except ImportError:  # pragma: no cover
    trace = None  # type: ignore

try:
    from correlation import (
        get_organization_id,
        get_request_id,
        get_user_id,
        get_workspace_id,
    )
except Exception:  # pragma: no cover
    def get_request_id():
        return None

    def get_user_id():
        return None

    def get_workspace_id():
        return None

    def get_organization_id():
        return None

AUDIT_LOG_PATH_ENV = "AUDIT_LOG_FILE"

_PLACEHOLDER_LOGGER = logging.getLogger("rag.config")
_TRUE_SET = {"1", "true", "yes", "on"}
_LOG_DIR_DEFAULT = os.path.join(os.path.dirname(__file__), "logs")
_AUDIT_DEFAULT = os.path.join(_LOG_DIR_DEFAULT, "audit.log")
AUDIT_LOG_PATH = os.getenv(AUDIT_LOG_PATH_ENV, _AUDIT_DEFAULT)


class JsonFormatter(logging.Formatter):
    """Structured log formatter producing JSON records."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info:
            log_record["stack_info"] = self.formatStack(record.stack_info)

        request_id = get_request_id()
        if request_id:
            log_record["request_id"] = request_id

        user_id = get_user_id()
        if user_id:
            log_record["user_id"] = user_id

        workspace_id = get_workspace_id()
        if workspace_id:
            log_record["workspace_id"] = workspace_id

        organization_id = get_organization_id()
        if organization_id:
            log_record["organization_id"] = organization_id

        if trace:
            span = trace.get_current_span()
            span_ctx = span.get_span_context() if span else None
            if span_ctx and span_ctx.trace_id:
                log_record["trace_id"] = f"{span_ctx.trace_id:032x}"
                log_record["span_id"] = f"{span_ctx.span_id:016x}"

        # Merge extra attributes
        record_dict = record.__dict__
        for key, value in record_dict.items():
            if key in ("args", "asctime", "created", "exc_text", "filename", "funcName",
                        "levelname", "levelno", "lineno", "message", "module", "msecs",
                        "msg", "name", "pathname", "process", "processName", "relativeCreated",
                        "stack_info", "thread", "threadName", "exc_info"):
                continue
            log_record[key] = value

        return json.dumps(log_record, ensure_ascii=False)


def configure_logging() -> logging.Logger:
    """Configure application logging with JSON console output and rotating file handler."""
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)

    global AUDIT_LOG_PATH
    AUDIT_LOG_PATH = os.getenv(AUDIT_LOG_PATH_ENV, os.path.join(log_dir, "audit.log"))

    logger = logging.getLogger("rag")
    logger.setLevel(logging.INFO)

    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "rag.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonFormatter())
    console_handler.setLevel(logging.INFO)

    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    audit_handler = RotatingFileHandler(
        AUDIT_LOG_PATH,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    audit_handler.setFormatter(JsonFormatter())
    audit_handler.setLevel(logging.INFO)

    audit_logger = logging.getLogger("rag.audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.handlers.clear()
    audit_logger.addHandler(audit_handler)

    return logger
