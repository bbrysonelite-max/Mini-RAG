"""
API key authentication utilities for FastAPI routes.

This module exposes helpers to extract API keys from incoming requests and
verify them against the `api_keys` table using `ApiKeyService`. It supports two
header conventions:

1. `X-API-Key: <key>`
2. `Authorization: ApiKey <key>`

All helpers return structured principals that include the key ID, owning user,
workspace context, and approved scopes. Callers can decide how to combine the
principal with JWT-authenticated users (e.g., prefer API key when present).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from fastapi import HTTPException, status
from starlette.requests import Request

from api_key_service import ApiKeyService, ApiKeyServiceError


@dataclass(frozen=True)
class APIKeyPrincipal:
    """Identity derived from a verified API key."""

    key_id: str
    user_id: str
    workspace_id: Optional[str]
    scopes: Tuple[str, ...]
    description: Optional[str] = None


_api_key_service: Optional[ApiKeyService] = None
_logger = logging.getLogger(__name__)


def configure_api_key_auth(service: Optional[ApiKeyService]) -> None:
    """
    Register the ApiKeyService used to validate keys.

    Passing None disables API key validation (falling back to JWT-only flows).
    """
    global _api_key_service
    _api_key_service = service


def _extract_api_key(request: Request) -> Optional[str]:
    """Return the API key from supported headers, if present."""
    header = request.headers.get("X-API-Key")
    if header:
        return header.strip()

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("apikey "):
        return auth_header.split(" ", 1)[1].strip()

    return None


async def get_api_key_principal(
    request: Request,
    scopes: Sequence[str] = ("read",),
    required: bool = False,
) -> Optional[APIKeyPrincipal]:
    """
    Attempt to authenticate via API key and return a principal if successful.

    Args:
        request: Incoming Starlette/FastAPI request.
        scopes: Expected scopes for the current route.
        required: When True, raises HTTPException(401/403) if the key is
                  missing/invalid/insufficient.

    Returns:
        APIKeyPrincipal or None when no API key is present and `required` is False.
    """
    if _api_key_service is None:
        if required:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API key authentication is not configured.",
            )
        return None

    api_key = _extract_api_key(request)
    if not api_key:
        if required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required.",
            )
        return None

    try:
        record = await _api_key_service.verify_api_key(api_key)
    except ApiKeyServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API key verification failed: {exc}",
        ) from exc

    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )

    granted_scopes = tuple(record.get("scopes") or [])
    missing_scopes = [scope for scope in scopes if scope not in granted_scopes]
    if missing_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key missing required scope(s): {', '.join(missing_scopes)}",
        )

    principal = APIKeyPrincipal(
        key_id=str(record["id"]),
        user_id=str(record["user_id"]),
        workspace_id=record.get("workspace_id"),
        scopes=granted_scopes,
        description=record.get("description"),
    )

    # Update audit trail (best effort).
    try:
        await _api_key_service.touch_last_used(principal.key_id)
    except Exception as exc:  # pragma: no cover - best effort logging
        _logger.debug("Failed to update last_used_at for API key %s: %s", principal.key_id, exc)

    return principal


class APIKeyAuth:
    """
    FastAPI dependency wrapper around `get_api_key_principal`.

    Example:

    ```python
    @router.get("/secured")
    async def secured_route(api_key: APIKeyPrincipal = Depends(APIKeyAuth(("write",)))):
        ...
    ```
    """

    def __init__(self, scopes: Sequence[str] = ("read",), required: bool = True):
        self._scopes = tuple(scopes)
        self._required = required

    async def __call__(self, request: Request) -> Optional[APIKeyPrincipal]:
        return await get_api_key_principal(
            request,
            scopes=self._scopes,
            required=self._required,
        )

