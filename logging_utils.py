import json
import logging
import os
from datetime import datetime
from typing import Any, Dict


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

    return logger
