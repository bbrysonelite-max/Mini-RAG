from __future__ import annotations

import logging
import os
from typing import Iterable, Optional, Set

_PLACEHOLDER_LOGGER = logging.getLogger("rag.config")
_TRUE_SET = {"1", "true", "yes", "on"}


def allow_insecure_defaults() -> bool:
    """Return True when placeholder secrets are allowed (development/test only)."""
    return os.getenv("ALLOW_INSECURE_DEFAULTS", "false").lower() in _TRUE_SET


def ensure_not_placeholder(
    name: str,
    value: Optional[str],
    placeholders: Optional[Iterable[str]] = None,
    *,
    required: bool = False,
    allow_insecure: Optional[bool] = None,
    logger: Optional[logging.Logger] = None,
) -> Optional[str]:
    """Validate that a configuration value is present and not a known placeholder.

    Args:
        name: Human-readable configuration name used in log/error messages.
        value: The configuration value to validate (often from os.getenv).
        placeholders: Iterable of unacceptable placeholder values.
        required: When True, absence or placeholder raises a RuntimeError unless
            ALLOW_INSECURE_DEFAULTS is enabled.
        allow_insecure: Optional override of the global flag.
        logger: Optional logger for warnings (defaults to rag.config logger).

    Returns:
        The original value when acceptable or ``None`` when blank.

    Raises:
        RuntimeError: If the value is blank/placeholder while insecure defaults are disabled.
    """

    if allow_insecure is None:
        allow_insecure = allow_insecure_defaults()
    log = logger or _PLACEHOLDER_LOGGER
    placeholder_set: Set[str] = set(placeholders or [])

    if value is None or value == "":
        if required and not allow_insecure:
            raise RuntimeError(f"{name} must be configured before starting the application.")
        if required:
            log.warning("%s is not set; running with empty value because ALLOW_INSECURE_DEFAULTS=true", name)
        return value

    if value in placeholder_set:
        if allow_insecure:
            log.warning("%s is using a placeholder value; do not use this in production.", name)
            return value
        raise RuntimeError(
            f"{name} is using a placeholder value. Provide a secure value or set ALLOW_INSECURE_DEFAULTS=true for development."
        )

    return value
