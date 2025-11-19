"""
API key management helpers.

This module is responsible for generating, storing, and revoking API keys.
Keys are stored in a hashed form (SHA-256) and are always returned to the caller
exactly once at creation time. The helper functions keep the logic contained so
that future API key authentication middleware can reuse the same primitives.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from database import Database

try:
    # psycopg is optional during unit testing; fall back gracefully otherwise.
    from psycopg.errors import UniqueViolation  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback when psycopg is absent
    UniqueViolation = None  # type: ignore[assignment]


DEFAULT_SCOPES: Tuple[str, ...] = ("read",)
_KEY_BYTES: int = 32  # 32 random bytes -> ~43 urlsafe characters
_PREFIX_LENGTH: int = 12  # short stable identifier for lookup/logging


class ApiKeyServiceError(Exception):
    """Raised when API key operations fail."""


class ApiKeyService:
    """
    Service responsible for creating, listing, verifying, and revoking API keys.

    The service expects the caller to supply a `Database` instance that is already
    initialised with an active connection pool.
    """

    def __init__(self, db: Database):
        self.db = db

    # -------------------------------------------------------------------------
    # Key generation & hashing helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _generate_plaintext_key(length_bytes: int = _KEY_BYTES) -> str:
        """
        Generate a cryptographically strong API key.

        token_urlsafe() yields URL-friendly characters and is adequate for bearer
        tokens. The length refers to the number of random bytes before base64
        conversion, so the resulting string is longer than length_bytes.
        """
        return secrets.token_urlsafe(length_bytes)

    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        """Return the SHA-256 hexadecimal digest of the API key."""
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    @staticmethod
    def _derive_prefix(api_key: str, length: int = _PREFIX_LENGTH) -> str:
        """
        Derive a deterministic prefix used for quick lookup.

        We hash the full key and slice the digest so the prefix never leaks the
        original secret yet remains stable for logging and database searches.
        """
        digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        return digest[:length]

    @staticmethod
    def _normalize_scopes(scopes: Optional[Sequence[str]]) -> Tuple[str, ...]:
        """Validate, deduplicate, and normalise scope entries."""
        if not scopes:
            scopes = DEFAULT_SCOPES
        cleaned: List[str] = []
        for scope in scopes:
            if not scope:
                continue
            value = scope.strip()
            if not value:
                continue
            cleaned.append(value)

        if not cleaned:
            cleaned = list(DEFAULT_SCOPES)

        # Deduplicate while preserving order
        deduped: List[str] = list(dict.fromkeys(cleaned))
        return tuple(deduped)

    # -------------------------------------------------------------------------
    # CRUD-style operations
    # -------------------------------------------------------------------------
    async def create_api_key(
        self,
        user_id: str,
        workspace_id: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new API key for the given user/workspace.

        Returns a dictionary that includes the plaintext API key under the
        `api_key` key; the caller is responsible for showing/storing it once.
        """
        plaintext_key = self._generate_plaintext_key()
        key_prefix = self._derive_prefix(plaintext_key)
        hashed_key = self._hash_api_key(plaintext_key)
        normalized_scopes = self._normalize_scopes(scopes)

        try:
            row = await self.db.fetch_one(
                """
                INSERT INTO api_keys (user_id, workspace_id, key_prefix, hashed_key, scopes, description)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, user_id, workspace_id, key_prefix, scopes, description,
                          created_at, last_used_at, revoked_at
                """,
                (user_id, workspace_id, key_prefix, hashed_key, list(normalized_scopes), description),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            if UniqueViolation and isinstance(exc, UniqueViolation):
                raise ApiKeyServiceError(
                    "An API key with the generated prefix already exists. Please retry issuing the key."
                ) from exc
            raise ApiKeyServiceError(f"Failed to create API key: {exc}") from exc

        if not row:
            raise ApiKeyServiceError("Database returned no data while creating API key.")

        row["scopes"] = list(row.get("scopes") or [])
        row["api_key"] = plaintext_key  # Only expose once to the caller
        return row

    async def list_api_keys(
        self,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        include_revoked: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return API keys filtered by user/workspace context."""
        try:
            rows = await self.db.fetch_all(
                """
                SELECT id, user_id, workspace_id, key_prefix, scopes, description,
                       created_at, last_used_at, revoked_at
                FROM api_keys
                WHERE ($1::uuid IS NULL OR user_id = $1::uuid)
                  AND ($2::uuid IS NULL OR workspace_id = $2::uuid)
                  AND ($3::boolean OR revoked_at IS NULL)
                ORDER BY created_at DESC
                """,
                (user_id, workspace_id, include_revoked),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            raise ApiKeyServiceError(f"Failed to list API keys: {exc}") from exc

        for row in rows:
            row["scopes"] = list(row.get("scopes") or [])
        return rows

    async def revoke_api_key(self, key_id: str, revoked_at: Optional[datetime] = None) -> bool:
        """Mark an API key as revoked. Returns True when a row was updated."""
        timestamp = revoked_at or datetime.now(timezone.utc)
        try:
            row = await self.db.fetch_one(
                """
                UPDATE api_keys
                SET revoked_at = $2
                WHERE id = $1 AND revoked_at IS NULL
                RETURNING id
                """,
                (key_id, timestamp),
            )
        except Exception as exc:  # pragma: no cover
            raise ApiKeyServiceError(f"Failed to revoke API key {key_id}: {exc}") from exc
        return bool(row)

    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Verify the supplied API key and return the matching record.

        This helper is intended for future authentication middleware. It leaves
        the caller responsible for applying additional business rules (scopes,
        rate limits, etc.).
        """
        key_prefix = self._derive_prefix(api_key)
        hashed_key = self._hash_api_key(api_key)
        try:
            row = await self.db.fetch_one(
                """
                SELECT id, user_id, workspace_id, key_prefix, scopes, description,
                       created_at, last_used_at, revoked_at
                FROM api_keys
                WHERE key_prefix = $1 AND hashed_key = $2 AND revoked_at IS NULL
                """,
                (key_prefix, hashed_key),
            )
        except Exception as exc:  # pragma: no cover
            raise ApiKeyServiceError(f"Failed to verify API key: {exc}") from exc

        if row:
            row["scopes"] = list(row.get("scopes") or [])
        return row

    async def touch_last_used(self, key_id: str, when: Optional[datetime] = None) -> None:
        """
        Update the last_used_at timestamp for observability.

        This method never raises if the update fails; failures are logged upstream
        rather than blocking the request path. Callers can opt into awaiting the
        result if they need stricter guarantees.
        """
        timestamp = when or datetime.now(timezone.utc)
        try:
            await self.db.execute(
                "UPDATE api_keys SET last_used_at = $2 WHERE id = $1",
                (key_id, timestamp),
            )
        except Exception:
            # Logging is deferred to the caller to avoid noisy traces here.
            pass

