"""
Lightweight Python SDK for Mini-RAG Enterprise API.

Usage:
    from clients.sdk import MiniRAGClient

    client = MiniRAGClient(
        base_url="https://mini-rag.example.com",
        api_key="your-api-key",
    )
    answer = client.ask("Summarize onboarding process.", k=5)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import httpx


class MiniRAGError(RuntimeError):
    """Raised when the API returns a non-success status."""


class MiniRAGClient:
    """Typed convenience wrapper around the REST API."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=self._default_headers(api_key),
            timeout=timeout,
        )

    @staticmethod
    def _default_headers(api_key: Optional[str]) -> Dict[str, str]:
        headers = {
            "User-Agent": "mini-rag-sdk/0.1",
            "Accept": "application/json",
        }
        if api_key:
            headers["X-API-Key"] = api_key
        return headers

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------ ask --
    def ask(self, query: str, *, k: int = 8, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        data = {"query": query, "k": str(k)}
        if workspace_id:
            data["workspace_id"] = workspace_id
        response = self._client.post("/api/v1/ask", data=data)
        return self._handle_response(response)

    # --------------------------------------------------------------- ingest --
    def ingest_urls(self, urls: Iterable[str], *, language: str = "en") -> Dict[str, Any]:
        payload = {
            "urls": "\n".join(urls),
            "language": language,
        }
        response = self._client.post("/api/v1/ingest/urls", data=payload)
        return self._handle_response(response)

    def ingest_files(self, paths: Iterable[Path], *, language: str = "en") -> Dict[str, Any]:
        files = [
            ("files", (path.name, path.read_bytes()))
            for path in paths
        ]
        response = self._client.post(
            "/api/v1/ingest/files",
            data={"language": language},
            files=files,
        )
        return self._handle_response(response)

    # --------------------------------------------------------------- sources --
    def list_sources(self) -> Dict[str, Any]:
        response = self._client.get("/api/v1/sources")
        return self._handle_response(response)

    # --------------------------------------------------------------- billing --
    def create_checkout_session(
        self,
        *,
        price_id: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "price_id": price_id,
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        response = self._client.post("/api/v1/billing/checkout", json=payload)
        return self._handle_response(response)

    def create_billing_portal_session(self, *, return_url: Optional[str] = None) -> Dict[str, Any]:
        payload = {"return_url": return_url}
        response = self._client.post("/api/v1/billing/portal", json=payload)
        return self._handle_response(response)

    # ------------------------------------------------------------ utilities --
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        if response.status_code >= 400:
            raise MiniRAGError(
                f"{response.status_code} {response.reason_phrase}: {response.text}"
            )
        if not response.content:
            return {}
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise MiniRAGError("Server returned invalid JSON") from exc

    def __enter__(self) -> "MiniRAGClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

