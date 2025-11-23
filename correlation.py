from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Dict, Mapping, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

try:  # pragma: no cover
    from opentelemetry import trace
except ImportError:  # pragma: no cover
    trace = None  # type: ignore

_request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_workspace_id_ctx: ContextVar[Optional[str]] = ContextVar("workspace_id", default=None)
_organization_id_ctx: ContextVar[Optional[str]] = ContextVar("organization_id", default=None)


def get_request_id() -> Optional[str]:
    return _request_id_ctx.get()


def get_user_id() -> Optional[str]:
    return _user_id_ctx.get()


def get_workspace_id() -> Optional[str]:
    return _workspace_id_ctx.get()


def get_organization_id() -> Optional[str]:
    return _organization_id_ctx.get()


def set_request_context(
    *,
    user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> None:
    if user_id is not None:
        _user_id_ctx.set(user_id)
    if workspace_id is not None:
        _workspace_id_ctx.set(workspace_id)
    if organization_id is not None:
        _organization_id_ctx.set(organization_id)


def build_observability_headers(additional: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """
    Build outbound headers that propagate request/trace context to downstream services.
    """
    headers: Dict[str, str] = {}
    request_id = get_request_id()
    if request_id:
        headers["X-Request-ID"] = request_id

    if trace:
        span = trace.get_current_span()
        if span:
            span_ctx = span.get_span_context()
            if span_ctx and span_ctx.trace_id:
                trace_id = f"{span_ctx.trace_id:032x}"
                span_id = f"{span_ctx.span_id:016x}"
                sampled = int(getattr(span_ctx.trace_flags, "value", int(span_ctx.trace_flags))) & 0x1  # type: ignore[arg-type]
                headers["traceparent"] = f"00-{trace_id}-{span_id}-{'01' if sampled else '00'}"

    if additional:
        for key, value in additional.items():
            if value is not None:
                headers[key] = value

    return headers


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that attaches/propagates X-Request-ID and resets per-request context.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        tokens = [
            (_request_id_ctx, _request_id_ctx.set(request_id)),
            (_user_id_ctx, _user_id_ctx.set(None)),
            (_workspace_id_ctx, _workspace_id_ctx.set(None)),
            (_organization_id_ctx, _organization_id_ctx.set(None)),
        ]
        request.scope["request_id"] = request_id

        try:
            response: Response = await call_next(request)
        finally:
            for var, token in tokens:
                var.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response
