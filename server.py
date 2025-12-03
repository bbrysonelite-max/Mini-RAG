import os, json, subprocess, hashlib, re, logging, asyncio, time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Sequence, Tuple, Set
from pathlib import Path
from fastapi import FastAPI, APIRouter, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware
from collections import deque

from retrieval import load_chunks, SimpleIndex, format_citation, get_unique_sources, get_chunks_by_source, delete_source_chunks
from score import score_answer
# Import ingestion functions directly from raglite for user_id support
from raglite import ingest_youtube, ingest_transcript, ingest_docs

from api_key_service import ApiKeyService
from api_key_auth import configure_api_key_auth, get_api_key_principal, APIKeyPrincipal

from chunk_backup import ChunkBackupError, create_chunk_backup
from background_queue import BackgroundTaskQueue
from quota_service import QuotaService, QuotaExceededError
from billing_service import BillingService, BillingServiceError

from correlation import (
    CorrelationIdMiddleware,
    build_observability_headers,
    get_organization_id,
    get_request_id,
    get_user_id,
    get_workspace_id,
    set_request_context,
)
from logging_utils import configure_logging, AUDIT_LOG_PATH
from telemetry import setup_tracing
from telemetry import setup_tracing
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
import httpx

try:
    from opentelemetry import trace
except ImportError:  # pragma: no cover
    trace = None  # type: ignore

# Import database (optional - server works without it)
try:
    from database import Database, init_database
    from user_service import UserService, get_user_service
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"Database module not available: {e}")
    DATABASE_AVAILABLE = False
    Database = None
    init_database = None
    UserService = None
    get_user_service = None

from config_utils import ensure_not_placeholder, allow_insecure_defaults

CHUNKS_PATH = os.environ.get("CHUNKS_PATH", "out/chunks.jsonl")
BACKGROUND_JOBS_ENABLED = os.getenv("BACKGROUND_JOBS_ENABLED", "false").lower() in {"1", "true", "yes"}
BACKGROUND_QUEUE: Optional[BackgroundTaskQueue] = None
ALLOW_INSECURE_DEFAULTS = allow_insecure_defaults()
# LOCAL_MODE: Skip authentication for local development/testing
LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() in {"1", "true", "yes"}
DEFAULT_SECRET_KEY = "change-this-secret-key-in-production"
SECRET_KEY_PLACEHOLDERS = {DEFAULT_SECRET_KEY, "changeme"}
_METRICS_WIRED = False
INDEX = None
CHUNKS = []
_chunk_count_cache: Optional[int] = None
_chunk_count_stamp: Optional[float] = None
API_DESCRIPTION = (
    "RAG Talking Agent backend.\n\n"
    "Versioned REST endpoints are available under `/api/v1`. "
    "Authentication supports Google OAuth JWTs and API keys (set `X-API-Key`)."
)

BASE_DIR = Path(__file__).resolve().parent
LEGACY_FRONTEND_DIR = BASE_DIR / "frontend"
REACT_FRONTEND_DIR = BASE_DIR / "frontend-react" / "dist"

app = FastAPI(
    title="RAG Talking Agent (with Ingest)",
    version="1.0.0",
    description=API_DESCRIPTION,
)
api_v1 = APIRouter(prefix="/api/v1", tags=["v1"])

# Metrics instrumentation
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(
    app,
    endpoint="/metrics",
    include_in_schema=False,
)

# CORS
_cors_origins = [origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if origin.strip()]
if not _cors_origins:
    _cors_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply common security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        csp = os.getenv(
            "CONTENT_SECURITY_POLICY",
            "default-src 'self'; base-uri 'self'; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'",
        )
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("Pragma", "no-cache")
        return response


app.add_middleware(SecurityHeadersMiddleware)


# Prometheus metrics for request/ingest observability
ASK_REQUEST_COUNTER = Counter(
    "ask_requests_total",
    "Total number of ask requests handled.",
    ["outcome", "status_code"],
)
ASK_LATENCY = Histogram(
    "ask_request_latency_seconds",
    "Latency of ask requests in seconds.",
    ["outcome"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
INGEST_COUNTER = Counter(
    "ingest_operations_total",
    "Total ingest operations processed (server-side).",
    ["source", "outcome", "status_code"],
)
INGEST_LATENCY = Histogram(
    "ingest_operation_latency_seconds",
    "Latency of ingest operations in seconds.",
    ["source", "outcome"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
CHUNK_COUNT_GAUGE = Gauge(
    "chunk_records_total",
    "Current number of chunk records available to the search index.",
)

WORKSPACE_QUOTA_USAGE = Gauge(
    "workspace_quota_usage",
    "Absolute per-workspace quota usage counters.",
    ["workspace_id", "metric"],
)

WORKSPACE_QUOTA_RATIO = Gauge(
    "workspace_quota_ratio",
    "Per-workspace quota utilization ratios (0-1).",
    ["workspace_id", "metric"],
)

QUOTA_EXCEEDED_COUNTER = Counter(
    "quota_exceeded_total",
    "Total count of requests rejected due to quota exhaustion.",
    ["workspace_id", "metric"],
)

EXTERNAL_REQUEST_ERRORS = Counter(
    "external_request_errors_total",
    "Count of upstream dependency errors.",
    ["service", "operation"],
)

INGEST_PROCESSED_CHUNKS = Counter(
    "ingest_processed_chunks_total",
    "Total number of chunks successfully ingested.",
    ["source"],
)


def _record_ingest_event(source: str, outcome: str, status_code: int) -> None:
    INGEST_COUNTER.labels(
        source=source,
        outcome=outcome,
        status_code=str(status_code),
    ).inc()


def _record_external_error(service: str, operation: str) -> None:
    EXTERNAL_REQUEST_ERRORS.labels(service=service, operation=operation).inc()

# Session middleware (required for OAuth)
def _ensure_not_placeholder(
    name: str,
    value: Optional[str],
    placeholders: Optional[Set[str]] = None,
    *,
    required: bool = False,
) -> Optional[str]:
    placeholders = placeholders or set()
    logger_local = logging.getLogger("rag.config")

    if value is None or value == "":
        if required and not ALLOW_INSECURE_DEFAULTS:
            raise RuntimeError(f"{name} must be configured before starting the application.")
        if required:
            logger_local.warning("%s is not set; running with empty value because ALLOW_INSECURE_DEFAULTS=true", name)
        return value

    if value in placeholders:
        if ALLOW_INSECURE_DEFAULTS:
            logger_local.warning("%s is using a placeholder value; do not use this in production.", name)
            return value
        raise RuntimeError(
            f"{name} is using a placeholder value. Provide a secure value or set ALLOW_INSECURE_DEFAULTS=true for development."
        )

    return value

SECRET_KEY_VALUE = ensure_not_placeholder(
    "SECRET_KEY",
    os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY),
    SECRET_KEY_PLACEHOLDERS,
    required=True,
)
app.add_middleware(SessionMiddleware, secret_key=(SECRET_KEY_VALUE or DEFAULT_SECRET_KEY))
app.add_middleware(CorrelationIdMiddleware)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class RequestTimer:
    """Context manager to measure request latency."""

    def __init__(self, operation: str, extra: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.extra = extra or {}
        self.start = None

    def __enter__(self):
        self.start = asyncio.get_event_loop().time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start is None:
            return
        duration = asyncio.get_event_loop().time() - self.start
        payload = {"operation": self.operation, "duration_ms": round(duration * 1000, 3)}
        payload.update(self.extra)
        logger.info("request_duration", extra=payload)


# Setup logging & telemetry
logger = configure_logging()
AUDIT_LOGGER = logging.getLogger("rag.audit")
setup_tracing(app)

# IMPORTANT: React frontend is the PRIMARY frontend at /app
# Legacy frontend is kept at /app-legacy for backwards compatibility only
if REACT_FRONTEND_DIR.exists():
    app.mount(
        "/app",
        StaticFiles(directory=str(REACT_FRONTEND_DIR), html=True),
        name="frontend",
    )
    logger.info("React frontend mounted at /app from %s", REACT_FRONTEND_DIR)
    # Also mount assets directory for React build
    react_assets_dir = REACT_FRONTEND_DIR / "assets"
    if react_assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(react_assets_dir)),
            name="react-assets",
        )
        logger.info("React assets mounted at /assets from %s", react_assets_dir)
else:
    logger.error("React frontend NOT FOUND at %s - this is required!", REACT_FRONTEND_DIR)
    # Fallback to legacy only if React is missing
    if LEGACY_FRONTEND_DIR.exists():
        app.mount(
            "/app",
            StaticFiles(directory=str(LEGACY_FRONTEND_DIR), html=True),
            name="frontend",
        )
        logger.warning("Falling back to legacy frontend at /app - React build is missing!")

# Legacy frontend available at /app-legacy for backwards compatibility
if LEGACY_FRONTEND_DIR.exists():
    app.mount(
        "/app-legacy",
        StaticFiles(directory=str(LEGACY_FRONTEND_DIR), html=True),
        name="legacy-frontend",
    )
    logger.info("Legacy frontend mounted at /app-legacy from %s", LEGACY_FRONTEND_DIR)

HEALTHCHECKS_PING_URL = os.getenv("HEALTHCHECKS_PING_URL")
HEALTHCHECKS_PING_FAIL_URL = os.getenv("HEALTHCHECKS_PING_FAIL_URL")


def _log_event(event: str, **fields: Any) -> None:
    """
    Emit structured JSON logs aligned with the UI observability dashboard.

    Non-primitive values are coerced to strings so logging never raises.
    """
    payload: Dict[str, Any] = {"event": event}
    for key, value in fields.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            payload[key] = value
        else:
            payload[key] = repr(value)

    if "request_id" not in payload:
        request_id = get_request_id()
        if request_id:
            payload["request_id"] = request_id

    if "user_id" not in payload:
        current_user_id = get_user_id()
        if current_user_id:
            payload["user_id"] = current_user_id

    if "workspace_id" not in payload:
        current_workspace_id = get_workspace_id()
        if current_workspace_id:
            payload["workspace_id"] = current_workspace_id

    if "organization_id" not in payload:
        current_org_id = get_organization_id()
        if current_org_id:
            payload["organization_id"] = current_org_id

    if trace:
        span = trace.get_current_span()
        if span:
            span_ctx = span.get_span_context()
            if span_ctx and span_ctx.trace_id:
                payload.setdefault("trace_id", f"{span_ctx.trace_id:032x}")
                payload.setdefault("span_id", f"{span_ctx.span_id:016x}")

    logger.info(event, extra=payload)
    if AUDIT_LOGGER.handlers:
        AUDIT_LOGGER.info(event, extra=payload)


def _quota_metrics_hook(workspace_id: str, settings: Dict[str, int], snapshot: Dict[str, int]) -> None:
    """Update Prometheus gauges for workspace quota usage and emit threshold logs."""
    requests_today = snapshot.get("request_count", 0)
    WORKSPACE_QUOTA_USAGE.labels(workspace_id, "requests_today").set(requests_today)
    daily_limit = max(settings.get("request_limit_per_day", 1), 1)
    daily_ratio = requests_today / daily_limit
    WORKSPACE_QUOTA_RATIO.labels(workspace_id, "requests_per_day").set(min(daily_ratio, 1.5))

    minute_requests = snapshot.get("minute_request_count", 0)
    WORKSPACE_QUOTA_USAGE.labels(workspace_id, "requests_current_minute").set(minute_requests)
    minute_limit = max(settings.get("request_limit_per_minute", 1), 1)
    minute_ratio = minute_requests / minute_limit
    WORKSPACE_QUOTA_RATIO.labels(workspace_id, "requests_per_minute").set(min(minute_ratio, 1.5))

    chunks_today = snapshot.get("chunk_count", 0)
    WORKSPACE_QUOTA_USAGE.labels(workspace_id, "chunks_today").set(chunks_today)

    chunk_total = snapshot.get("current_chunk_total")
    if chunk_total is not None:
        WORKSPACE_QUOTA_USAGE.labels(workspace_id, "chunk_total").set(chunk_total)
        chunk_limit = max(settings.get("chunk_limit", 1), 1)
        storage_ratio = chunk_total / chunk_limit
        WORKSPACE_QUOTA_RATIO.labels(workspace_id, "chunk_storage").set(min(storage_ratio, 1.5))
    else:
        storage_ratio = None

    for metric, ratio in (
        ("requests_per_day", daily_ratio),
        ("requests_per_minute", minute_ratio),
        ("chunk_storage", storage_ratio),
    ):
        if ratio is None:
            continue
        if ratio >= 0.9:
            _log_event(
                "quota.threshold",
                workspace_id=workspace_id,
                metric=metric,
                ratio=round(ratio, 3),
            )


async def _ping_healthchecks(success: bool, payload: Dict[str, Any]) -> None:
    """Send uptime pings to Healthchecks or similar services when configured."""
    if not HEALTHCHECKS_PING_URL:
        return

    url = HEALTHCHECKS_PING_URL if success else (HEALTHCHECKS_PING_FAIL_URL or f"{HEALTHCHECKS_PING_URL}/fail")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = build_observability_headers({"Content-Type": "application/json"})
            await client.post(url, json=payload, headers=headers)
        if success:
            _log_event("healthcheck.ping_sent", url=url, status="ok")
    except Exception as exc:
        _log_event("healthcheck.ping_failed", url=url, error=str(exc))
        logger.warning("Failed to ping health monitor: %s", exc)

async def _get_primary_workspace_id_for_user(user: Optional[Dict[str, Any]]) -> Optional[str]:
    """Resolve the user's default workspace ID, if multi-tenant support is enabled."""
    if not user or not USER_SERVICE:
        return None
    user_id = user.get("user_id")
    if not user_id:
        return None
    try:
        workspace = await USER_SERVICE.get_primary_workspace(user_id)
        return workspace.get("id") if workspace else None
    except Exception as exc:
        logger.warning(f"Unable to resolve primary workspace for user {user_id}: {exc}")
        return None


async def _get_organization_id_for_workspace(workspace_id: Optional[str]) -> Optional[str]:
    if not workspace_id or DB is None:
        return None
    row = await DB.fetch_one(
        "SELECT organization_id FROM workspaces WHERE id = $1",
        (workspace_id,),
    )
    if not row:
        return None
    return row.get("organization_id")

async def _resolve_auth_context(
    request: Request,
    scopes: Sequence[str] = ("read",),
    require: bool = False
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[APIKeyPrincipal]]:
    """
    Determine the caller identity using API keys (preferred) or JWT cookies.

    Returns (user, workspace_id, api_key_principal).
    """
    api_key_principal = await get_api_key_principal(request, scopes=scopes, required=False)
    if api_key_principal:
        user: Optional[Dict[str, Any]] = None
        if USER_SERVICE:
            try:
                user = await USER_SERVICE.get_user_by_id(api_key_principal.user_id)
            except Exception as exc:
                logger.warning(
                    "Failed to load user %s for API key %s: %s",
                    api_key_principal.user_id,
                    api_key_principal.key_id,
                    exc,
                )
        if not user:
            user = {
                "user_id": api_key_principal.user_id,
                "role": "api_key",
            }
        workspace_id = api_key_principal.workspace_id
        if workspace_id is None:
            workspace_id = await _get_primary_workspace_id_for_user(user)
        organization_id = await _get_organization_id_for_workspace(workspace_id)
        set_request_context(
            user_id=user.get("user_id") if user else None,
            workspace_id=workspace_id,
            organization_id=organization_id,
        )
        return user, workspace_id, api_key_principal

    user = get_current_user(request)
    if require and not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Supply an API key or sign in via Google OAuth.",
        )
    workspace_id = await _get_primary_workspace_id_for_user(user)
    organization_id = await _get_organization_id_for_workspace(workspace_id)
    set_request_context(
        user_id=user.get("user_id") if user else None,
        workspace_id=workspace_id,
        organization_id=organization_id,
    )
    return user, workspace_id, None


async def _consume_workspace_quota(
    workspace_id: Optional[str],
    *,
    request_delta: int = 0,
    chunk_delta: int = 0,
    current_chunk_total: Optional[int] = None,
) -> None:
    if not workspace_id or QUOTA_SERVICE is None:
        return
    try:
        await QUOTA_SERVICE.consume(
            workspace_id,
            request_delta=request_delta,
            chunk_delta=chunk_delta,
            current_chunk_total=current_chunk_total,
        )
    except QuotaExceededError as exc:
        metric = getattr(exc, "limit", "unknown")
        QUOTA_EXCEEDED_COUNTER.labels(
            workspace_id=workspace_id,
            metric=str(metric),
        ).inc()
        raise HTTPException(status_code=429, detail=str(exc)) from exc


async def _count_workspace_chunks(workspace_id: Optional[str]) -> Optional[int]:
    if not workspace_id:
        return None
    if not os.path.exists(CHUNKS_PATH):
        return 0

    loop = asyncio.get_running_loop()

    def _count() -> int:
        count = 0
        try:
            with open(CHUNKS_PATH, "r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if payload.get("workspace_id") == workspace_id:
                        count += 1
        except FileNotFoundError:
            return 0
        return count

    return await loop.run_in_executor(None, _count)


async def _require_billing_active(workspace_id: Optional[str]) -> None:
    """Block ingestion when billing is inactive for the associated organization."""
    if not workspace_id or DB is None:
        return
    row = await DB.fetch_one(
        """
        SELECT
            o.billing_status,
            o.trial_ends_at,
            o.subscription_expires_at
        FROM workspaces w
        JOIN organizations o ON o.id = w.organization_id
        WHERE w.id = $1
        """,
        (workspace_id,),
    )
    if not row:
        return
    status = (row.get("billing_status") or "trialing").lower()
    now = datetime.now(timezone.utc)
    if status == "trialing":
        trial_end = row.get("trial_ends_at")
        if trial_end and trial_end < now:
            _log_event("billing.blocked", workspace_id=workspace_id, reason="trial_expired")
            raise HTTPException(
                status_code=402,
                detail="Trial period ended. Please subscribe to continue ingesting.",
            )
        return
    if status == "active":
        expires_at = row.get("subscription_expires_at")
        if expires_at and expires_at < now:
            _log_event("billing.blocked", workspace_id=workspace_id, reason="subscription_expired")
            raise HTTPException(
                status_code=402,
                detail="Subscription expired. Update billing information to ingest new data.",
            )
        return

    _log_event("billing.blocked", workspace_id=workspace_id, reason=status)
    raise HTTPException(
        status_code=402,
        detail=f"Workspace billing status '{status}' does not permit ingestion.",
    )


async def _warm_search_index() -> None:
    """Load the search index on startup so the first query avoids cold-start penalties."""
    if not os.path.exists(CHUNKS_PATH):
        return
    start = time.perf_counter()
    try:
        await asyncio.to_thread(ensure_index)
    except Exception as exc:
        _log_event("index.warm_failed", error=str(exc))
        logger.warning("Index warmup failed: %s", exc)
    else:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        _log_event(
            "index.warm_completed",
            duration_ms=duration_ms,
            chunk_count=len(CHUNKS),
        )
        CHUNK_COUNT_GAUGE.set(len(CHUNKS))
        logger.info("Index warmup completed in %sms (chunks=%s)", duration_ms, len(CHUNKS))


async def _record_query_baseline() -> None:
    """Capture a baseline ask latency sample for dashboards."""
    start = time.perf_counter()
    try:
        await asyncio.to_thread(_process_query, "baseline measurement", 1, {}, None)
    except IndexNotFoundError:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        ASK_LATENCY.labels(outcome="baseline_noindex").observe(max(duration_ms / 1000.0, 0.0))
        _log_event(
            "ask.baseline_skipped",
            reason="index_not_found",
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        ASK_LATENCY.labels(outcome="baseline_error").observe(max(duration_ms / 1000.0, 0.0))
        _log_event(
            "ask.baseline_failed",
            error=str(exc),
            duration_ms=duration_ms,
        )
        logger.warning("Baseline ask measurement failed: %s", exc)
    else:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        ASK_LATENCY.labels(outcome="baseline").observe(max(duration_ms / 1000.0, 0.0))
        _log_event(
            "ask.baseline_completed",
            duration_ms=duration_ms,
        )
        logger.info("Baseline ask completed in %sms", duration_ms)


async def _warm_and_measure() -> None:
    await _warm_search_index()
    await _record_query_baseline()

# Custom exceptions
class RAGError(Exception):
    """Base exception for RAG system."""
    pass

class IndexNotFoundError(RAGError):
    """Raised when index is not found or cannot be loaded."""
    pass

class InvalidQueryError(RAGError):
    """Raised when query is invalid."""
    pass

class IngestionError(RAGError):
    """Raised when ingestion fails."""
    pass

# Exception handlers
@app.exception_handler(RAGError)
async def rag_error_handler(request: Request, exc: RAGError):
    """Handle RAG-specific errors."""
    logger.error(f"RAG Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=400,
        content={
            "error": str(exc) or "An error occurred processing your request",
            "type": type(exc).__name__
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors without exposing internal details."""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "An internal error occurred. Please try again later."}
    )

# Import auth module (optional - server works without it)
try:
    from auth import oauth, create_access_token, get_current_user, require_auth
    from fastapi.responses import RedirectResponse
    AUTH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Auth module not available: {e}")
    AUTH_AVAILABLE = False
    oauth = None
    def create_access_token(*args, **kwargs): raise NotImplementedError("Auth not configured")
    def get_current_user(*args, **kwargs): return None
    def require_auth(*args, **kwargs): raise NotImplementedError("Auth not configured")
    from fastapi.responses import RedirectResponse

# Pydantic models for input validation
class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000, description="Search query")
    k: int = Field(8, ge=1, le=100, description="Number of results")
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()

class IngestURLRequest(BaseModel):
    urls: str = Field(..., description="URLs, one per line")
    language: str = Field("en", pattern=r'^[a-z]{2}(-[A-Z]{2})?$', description="Language code")
    
    @validator('urls')
    def validate_urls(cls, v):
        lines = [u.strip() for u in v.splitlines() if u.strip()]
        if len(lines) > 100:
            raise ValueError('Maximum 100 URLs per request')
        return v


class BillingCheckoutRequest(BaseModel):
    price_id: Optional[str] = Field(None, description="Stripe price identifier")
    success_url: Optional[str] = Field(None, description="Override success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Override cancel redirect URL")


class BillingPortalRequest(BaseModel):
    return_url: Optional[str] = Field(None, description="Return URL after managing billing")

# Security configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.md', '.markdown', '.txt', '.vtt', '.srt'}
UPLOAD_DIR = Path("uploads")

def sanitize_filename(filename: str) -> str:
    """Remove path components and dangerous characters."""
    name = os.path.basename(filename)
    name = name.replace('/', '').replace('\\', '')
    name = ''.join(c for c in name if c.isalnum() or c in '.-_')
    if len(name) > 255:
        name = name[:255]
    return name

def validate_file_type(filename: str) -> bool:
    """Check if file extension is allowed."""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS

def generate_safe_filename(original_filename: str) -> str:
    """Generate a safe, unique filename."""
    sanitized = sanitize_filename(original_filename)
    name_hash = hashlib.md5(sanitized.encode()).hexdigest()[:8]
    return f"{name_hash}_{sanitized}"

# Database and user service globals
DB: Optional[Database] = None
USER_SERVICE: Optional[UserService] = None
API_KEY_SERVICE: Optional[ApiKeyService] = None
QUOTA_SERVICE: Optional[QuotaService] = None
BILLING_SERVICE: Optional[BillingService] = None

STRIPE_API_KEY = ensure_not_placeholder(
    "STRIPE_API_KEY",
    os.getenv("STRIPE_API_KEY"),
    {"sk_test_placeholder"},
    required=False,
)
STRIPE_WEBHOOK_SECRET = ensure_not_placeholder(
    "STRIPE_WEBHOOK_SECRET",
    os.getenv("STRIPE_WEBHOOK_SECRET"),
    {"whsec_placeholder"},
    required=False,
)
STRIPE_PRICE_ID = ensure_not_placeholder(
    "STRIPE_PRICE_ID",
    os.getenv("STRIPE_PRICE_ID"),
    {"price_123"},
    required=False,
)
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:8000/app/billing/success")
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "http://localhost:8000/app/billing/cancel")
STRIPE_PORTAL_RETURN_URL = os.getenv("STRIPE_PORTAL_RETURN_URL", "http://localhost:8000/app/settings/billing")

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup (if configured)."""
    global DB, USER_SERVICE, API_KEY_SERVICE, QUOTA_SERVICE, BILLING_SERVICE, BACKGROUND_QUEUE
    
    # Try to initialize database if connection string is provided
    db_url = os.environ.get("DATABASE_URL")
    if db_url and DATABASE_AVAILABLE:
        try:
            DB = await init_database(db_url, init_schema=False)
            USER_SERVICE = get_user_service(DB)
            API_KEY_SERVICE = ApiKeyService(DB)
            QUOTA_SERVICE = QuotaService(DB, metrics_hook=_quota_metrics_hook)
            configure_api_key_auth(API_KEY_SERVICE)
            BILLING_SERVICE = None
            if STRIPE_API_KEY:
                try:
                    BILLING_SERVICE = BillingService(
                        DB,
                        STRIPE_API_KEY,
                        webhook_secret=STRIPE_WEBHOOK_SECRET,
                        default_price_id=STRIPE_PRICE_ID,
                        default_success_url=STRIPE_SUCCESS_URL,
                        default_cancel_url=STRIPE_CANCEL_URL,
                        default_portal_return_url=STRIPE_PORTAL_RETURN_URL,
                    )
                    logger.info("Billing service initialized.")
                except BillingServiceError as exc:
                    BILLING_SERVICE = None
                    logger.warning("Billing service disabled: %s", exc)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize database: {e}")
            logger.warning("Server will run without database features")
            DB = None
            USER_SERVICE = None
            API_KEY_SERVICE = None
            QUOTA_SERVICE = None
            BILLING_SERVICE = None
            configure_api_key_auth(None)
    else:
        logger.info("No DATABASE_URL configured - running without database")
        configure_api_key_auth(None)
        QUOTA_SERVICE = None
        BILLING_SERVICE = None
    asyncio.create_task(_warm_and_measure())

    if INDEX is None or not CHUNKS:
        ensure_index()

    if BACKGROUND_JOBS_ENABLED:
        BACKGROUND_QUEUE = BackgroundTaskQueue()
        await BACKGROUND_QUEUE.start()
        logger.info("Background job queue started")
    else:
        BACKGROUND_QUEUE = None

    configure_logging()
    setup_tracing(app)

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    global DB, BACKGROUND_QUEUE
    if DB:
        # Database cleanup if needed
        try:
            await DB.close()
        except Exception:
            pass
        DB = None
    if BACKGROUND_QUEUE:
        try:
            await BACKGROUND_QUEUE.stop()
        except Exception:
            logger.warning("Failed to stop background queue", exc_info=True)
        BACKGROUND_QUEUE = None

def _count_lines(path):
    global _chunk_count_cache, _chunk_count_stamp
    try:
        modified = os.path.getmtime(path)
    except OSError:
        _chunk_count_cache = 0
        _chunk_count_stamp = None
        CHUNK_COUNT_GAUGE.set(0)
        return 0

    if _chunk_count_cache is not None and _chunk_count_stamp == modified:
        return _chunk_count_cache

    try:
        with open(path, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f)
    except FileNotFoundError:
        count = 0

    _chunk_count_cache = count
    _chunk_count_stamp = modified
    CHUNK_COUNT_GAUGE.set(count)
    return count

def is_admin(user: Optional[Dict[str, Any]]) -> bool:
    """Check if user has admin role."""
    if not user:
        return False
    return user.get('role') == 'admin'

def require_admin(user: Optional[Dict[str, Any]], api_key: Optional[APIKeyPrincipal] = None):
    """Raise exception if user is not admin."""
    if api_key and "admin" in api_key.scopes:
        return
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )
    if not is_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required."
        )

def ensure_index():
    global INDEX, CHUNKS
    if INDEX is None:
        if not os.path.exists(CHUNKS_PATH):
            logger.error(f"Index not found at {CHUNKS_PATH}")
            raise IndexNotFoundError("Index not found. Please ingest documents first.")
        try:
            CHUNKS = load_chunks(CHUNKS_PATH)
        except Exception as e:
            logger.error(f"Failed to load chunks: {e}", exc_info=True)
            raise IndexNotFoundError("Failed to load index. Please try rebuilding.")
        if not CHUNKS:
            raise IndexNotFoundError("Index is empty. Please ingest documents first.")
        try:
            INDEX = SimpleIndex(CHUNKS)
            logger.info("Search index rebuilt", extra={"chunks": len(CHUNKS)})
        except Exception as e:
            logger.error(f"Failed to build index: {e}", exc_info=True)
            raise IndexNotFoundError("Failed to build search index.")

@app.get("/")
def root(): return HTMLResponse('<meta http-equiv="refresh" content="0; url=/app/">')

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring (public)."""
    try:
        # Check if index exists
        if os.path.exists(CHUNKS_PATH):
            chunks_count = _count_lines(CHUNKS_PATH)
            index_status = "healthy" if chunks_count > 0 else "empty"
        else:
            index_status = "not_found"
            chunks_count = 0
        
        # Check database connection
        db_status = "not_configured"
        if DB:
            try:
                await DB.fetch_one("SELECT 1")
                db_status = "healthy"
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                db_status = "unhealthy"
        
        response = {
            "status": "healthy",
            "database": db_status,
            "index": index_status,
            "chunks_count": chunks_count,
            "auth_available": AUTH_AVAILABLE
        }
        asyncio.create_task(_ping_healthchecks(True, response))
        return response
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        failure_payload = {
            "status": "unhealthy",
            "error": str(e)
        }
        asyncio.create_task(_ping_healthchecks(False, failure_payload))
        return failure_payload

# OAuth Routes
@app.get("/auth/google")
async def google_auth(request: Request):
    """Initiate Google OAuth login."""
    if not AUTH_AVAILABLE:
        raise HTTPException(status_code=500, detail="OAuth not available. Please install auth dependencies.")
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        raise HTTPException(status_code=500, detail="OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
    
    try:
        # Check if oauth.google is registered
        if not hasattr(oauth, 'google') or oauth.google is None:
            raise HTTPException(status_code=500, detail="OAuth client not initialized. Check your .env credentials.")
        
        # Build redirect URI manually
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/auth/google/callback"
        logger.info(f"Redirect URI: {redirect_uri}")
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"OAuth redirect error: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")

@app.get("/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback."""
    if not AUTH_AVAILABLE:
        raise HTTPException(status_code=500, detail="OAuth not available.")
    try:
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info from Google
        user_info = None
        access_token = None
        
        if isinstance(token, dict):
            access_token = token.get("access_token")
            # Try to get userinfo from token response
            user_info = token.get("userinfo")
        
        # Fetch user info from Google API using access token
        if access_token and not user_info:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    headers = build_observability_headers({"Authorization": f"Bearer {access_token}"})
                    resp = await client.get(
                        "https://www.googleapis.com/oauth2/v2/userinfo",
                        headers=headers,
                        timeout=10.0
                    )
                    resp.raise_for_status()
                    user_info = resp.json()
                    logger.info("Successfully fetched user info from Google API")
            except Exception as fetch_error:
                logger.error(f"Failed to fetch user info: {fetch_error}")
                import traceback
                logger.error(traceback.format_exc())
                user_info = None
        
        if not user_info:
            logger.error("Failed to get user info from OAuth token")
            return RedirectResponse(url="/app/?error=auth_failed")
        
        # Extract user data
        email = user_info.get("email") or user_info.get("email_address")
        name = user_info.get("name") or (user_info.get("given_name", "") + " " + user_info.get("family_name", "")).strip()
        picture = user_info.get("picture")
        sub = user_info.get("sub") or user_info.get("id")
        
        if not email or not sub:
            logger.error(f"Incomplete user info: email={email}, sub={sub}, user_info keys: {list(user_info.keys()) if isinstance(user_info, dict) else 'not a dict'}")
            return RedirectResponse(url="/app/?error=auth_failed")
        
        # Save or update user in database (if available)
        user_id = None
        user_role = 'reader'  # default role
        if USER_SERVICE:
            try:
                db_user = await USER_SERVICE.create_or_update_user(
                    email=email,
                    name=name,
                    oauth_sub=sub,
                    picture=picture
                )
                if db_user:
                    user_id = str(db_user['id'])
                    user_role = db_user['role']
                    logger.info(f"User {email} saved to database with role: {user_role}")
            except Exception as e:
                logger.error(f"Failed to save user to database: {e}", exc_info=True)
                # Continue anyway - auth can work without database
        
        # Create JWT token
        jwt_payload = {
            "email": email,
            "name": name,
            "picture": picture,
            "sub": sub,
        }
        # Add user_id and role if we have them from database
        if user_id:
            jwt_payload["user_id"] = user_id
            jwt_payload["role"] = user_role
        
        jwt_token = create_access_token(jwt_payload)
        
        # Redirect to app with token in cookie
        response = RedirectResponse(url="/app/")
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=60 * 60 * 24 * 7  # 7 days
        )
        return response
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return RedirectResponse(url="/app/?error=auth_failed")

@app.get("/auth/logout")
async def logout():
    """Logout user by clearing cookie."""
    response = RedirectResponse(url="/app/")
    response.delete_cookie("access_token")
    return response

@app.get("/auth/me")
async def get_me(request: Request):
    """Get current user information."""
    # LOCAL_MODE: Return authenticated for local development
    if LOCAL_MODE:
        return {
            "authenticated": True,
            "user": {
                "user_id": "local-dev-user",
                "email": "local@localhost",
                "name": "Local Developer",
                "role": "admin",
            },
            "workspace_id": None,
            "via_api_key": False,
            "local_mode": True,
        }
    
    user, workspace_id, api_key = await _resolve_auth_context(request, scopes=("read",), require=False)
    if user or api_key:
        return {
            "authenticated": True,
            "user": user,
            "workspace_id": workspace_id,
            "via_api_key": api_key is not None,
        }
    return {"authenticated": False}

@app.post(
    "/ask",
    summary="Query the RAG system",
    description="Submit a natural language question and retrieve relevant chunks with AI-generated answers. Requires authentication (JWT or API key with read scope). Rate limited to 30 requests/minute.",
    response_description="Answer text, score metrics, and retrieved source chunks",
    tags=["Query"]
)
@limiter.limit("30/minute")
async def ask(request: Request, query: str = Form(...), k: int = Form(8)):
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("read",),
        require=True,
    )
    user_id = user.get("user_id") if user else None

    # Validate input
    try:
        ask_req = AskRequest(query=query, k=k)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    await _consume_workspace_quota(workspace_id, request_delta=1)

    # Add timeout for query processing
    import asyncio
    start_time = asyncio.get_event_loop().time()
    outcome = "success"
    status_code = 200
    try:
        with RequestTimer(
            "ask",
            {"user_id": user_id, "workspace_id": workspace_id, "api_key": bool(api_key_principal)},
        ):
            result = await asyncio.wait_for(
                asyncio.to_thread(_process_query, ask_req.query, ask_req.k, user, workspace_id),
                timeout=30.0  # 30 second timeout
            )
        _log_event(
            "ask.completed",
            user_id=user_id,
            workspace_id=workspace_id,
            api_key=bool(api_key_principal),
            query=ask_req.query[:200],
            k=ask_req.k,
            result_count=len(result.get("chunks", [])),
        )
        return result
    except asyncio.TimeoutError:
        outcome = "timeout"
        status_code = 504
        raise HTTPException(
            status_code=504,
            detail="Request timed out. Please try a simpler query or contact support."
        )
    except HTTPException as exc:
        outcome = "error"
        status_code = exc.status_code
        raise
    except Exception:
        outcome = "error"
        status_code = 500
        raise
    finally:
        duration = asyncio.get_event_loop().time() - start_time
        ASK_REQUEST_COUNTER.labels(outcome=outcome, status_code=str(status_code)).inc()
        ASK_LATENCY.labels(outcome=outcome).observe(duration)

def _process_query(query: str, k: int, user: Dict[str, Any], workspace_id: Optional[str] = None):
    """Process query synchronously (called from async context)."""
    ensure_index()
    # Filter by user_id for data isolation
    user_id = user.get('user_id') if user else None
    ranked = INDEX.search(query, k=k, user_id=user_id, workspace_id=workspace_id)
    top = [CHUNKS[i] for i,_ in ranked]
    snippets = [c.get("content","").strip() for c in top[:3]]
    cites = [format_citation(c) for c in top[:3]]
    text = " ".join(snippets)
    if len(text) > 900: text = text[:900].rsplit(" ",1)[0]+"…"
    ans = f"{text}\n\nSources:\n" + "\n".join(f"- {u}" for u in cites)
    sc = score_answer(query, ans, top)
    
    # Enhanced chunk details with scores and positions
    chunk_details = []
    for idx, (i, score) in enumerate(ranked):
        chunk = CHUNKS[i]
        meta = chunk.get("metadata", {})
        chunk_details.append({
            "index": idx + 1,
            "content": chunk.get("content", "").strip(),
            "score": float(score),
            "citation": format_citation(chunk),
            "source": chunk.get("source", {}),
            "metadata": {
                "chunk_index": meta.get("chunk_index"),
                "chunk_count": meta.get("chunk_count"),
                "start_sec": meta.get("start_sec"),
                "end_sec": meta.get("end_sec"),
                "language": meta.get("language", "en")
            }
        })
    
    return {
        "answer": ans,
        "citations": cites,
        "score": sc,
        "count": _count_lines(CHUNKS_PATH),
        "chunks": chunk_details
    }

@app.get(
    "/api/stats",
    summary="Get system statistics",
    description="Returns basic system stats including total chunk count. Useful for dashboard widgets.",
    tags=["System"]
)
def stats():
    return {"count": _count_lines(CHUNKS_PATH)}

# Also expose on v1
api_v1.get(
    "/stats",
    summary="Get system statistics",
    description="Returns basic system stats including total chunk count. Useful for dashboard widgets.",
    tags=["System"]
)(stats)


@api_v1.get("/jobs")
async def list_jobs(request: Request, limit: int = 50):
    if not BACKGROUND_JOBS_ENABLED or not BACKGROUND_QUEUE:
        raise HTTPException(status_code=503, detail="Background jobs are disabled.")
    await _resolve_auth_context(request, scopes=("write",), require=True)
    try:
        limit = max(1, min(200, int(limit)))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid limit parameter")
    return {"jobs": BACKGROUND_QUEUE.list_jobs(limit=limit)}


def validate_youtube_url(url: str) -> bool:
    """Validate YouTube URL format."""
    youtube_patterns = [
        r'^https?://(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(www\.)?youtube\.com/embed/[\w-]+',
        r'^https?://youtu\.be/[\w-]+',
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)

@app.post("/api/ingest_urls")
@app.post("/ingest/urls")
@limiter.limit("10/hour")
async def ingest_urls(request: Request, urls: str = Form(...), language: str = Form("en")):
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("write",),
        require=True,
    )
    user_id = user.get("user_id") if user else None
    await _require_billing_active(workspace_id)

    # Validate input
    try:
        url_req = IngestURLRequest(urls=urls, language=language)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    urls_list = [u.strip() for u in url_req.urls.splitlines() if u.strip()]

    if BACKGROUND_JOBS_ENABLED and BACKGROUND_QUEUE and urls_list:
        async def job_runner():
            return await _ingest_urls_core(user, workspace_id, api_key_principal, url_req, urls_list)

        job = BACKGROUND_QUEUE.submit(
            "ingest_urls",
            job_runner,
            metadata={
                "workspace_id": workspace_id,
                "user_id": user_id,
                "language": url_req.language,
                "url_count": len(urls_list),
            },
        )
        _log_event(
            "ingest.urls.queued",
            workspace_id=workspace_id,
            user_id=user_id,
            job_id=job.id,
            language=url_req.language,
            url_count=len(urls_list),
        )
        return {"job_id": job.id, "queued": True, "status": "queued"}

    return await _ingest_urls_core(user, workspace_id, api_key_principal, url_req, urls_list)


async def _ingest_urls_core(
    user: Optional[Dict[str, Any]],
    workspace_id: Optional[str],
    api_key_principal: Optional[APIKeyPrincipal],
    url_req: IngestURLRequest,
    urls_list: List[str],
) -> Dict[str, Any]:
    user_id = user.get("user_id") if user else None
    results: List[Dict[str, Any]] = []
    total = 0
    await _consume_workspace_quota(workspace_id, request_delta=1)
    current_chunk_total = await _count_workspace_chunks(workspace_id)

    for url in urls_list:
        # Validate YouTube URL format
        if not validate_youtube_url(url):
            results.append({"url": url, "error": "Invalid YouTube URL format", "written": 0})
            _log_event(
                "ingest.youtube.skipped",
                url=url,
                reason="invalid_format",
                user_id=user_id,
                workspace_id=workspace_id,
                api_key=bool(api_key_principal),
            )
            _record_ingest_event("youtube", "skipped", 400)
            continue
        start_time = time.perf_counter()
        primary_outcome = "success"
        try:
            with RequestTimer(
                "ingest_youtube",
                {"url": url, "user_id": user_id, "workspace_id": workspace_id, "api_key": bool(api_key_principal)},
            ):
                r = ingest_youtube(
                    url,
                    out_jsonl=CHUNKS_PATH,
                    language=url_req.language,
                    user_id=user_id,
                    workspace_id=workspace_id
                )
            written = r.get("written", 0)
            if written == 0 and r.get("stderr"):
                error_msg = r.get("stderr", "Unknown error")
                logger.warning(f"YouTube ingestion failed for {url}: {error_msg}")
                results.append({"url": url, "written": 0, "mode": "transcript", "error": error_msg})
                _log_event(
                    "ingest.youtube.failed",
                    url=url,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    api_key=bool(api_key_principal),
                    error=error_msg,
                    stage="primary",
                )
                _record_ingest_event("youtube", "failure", 500)
                primary_outcome = "failure"
            else:
                results.append({"url": url, "written": written, "mode": "transcript"})
                _log_event(
                    "ingest.youtube.completed",
                    url=url,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    api_key=bool(api_key_principal),
                    written=written,
                    language=url_req.language,
                    mode="transcript",
                )
                _record_ingest_event("youtube", "success", 200)
                if written:
                    INGEST_PROCESSED_CHUNKS.labels(source="youtube").inc(written)
            total += written
        except Exception as exc:
            logger.error(f"Error ingesting YouTube URL {url}: {exc}", exc_info=True)
            _log_event(
                "ingest.youtube.failed",
                url=url,
                user_id=user_id,
                workspace_id=workspace_id,
                api_key=bool(api_key_principal),
                error=str(exc),
                stage="primary_exception",
            )
            _record_ingest_event("youtube", "failure", 500)
            # fallback: fetch auto-captions via yt-dlp, then ingest .vtt
            vid = ""
            primary_outcome = "failure"
            try:
                vid = subprocess.check_output(
                    ["yt-dlp", "--print", "id", "--skip-download", url],
                    text=True,
                    timeout=30,
                    stderr=subprocess.DEVNULL
                ).strip().splitlines()[0]
            except subprocess.TimeoutExpired:
                logger.warning(f"yt-dlp timeout for {url}")
                vid = ""
            except Exception as yt_err:
                logger.warning(f"yt-dlp failed for {url}: {yt_err}")
                vid = ""
            vtt = ""
            try:
                subprocess.check_call(
                    ["yt-dlp", "--skip-download", "--write-auto-sub",
                     "--sub-lang", url_req.language, "--sub-format", "vtt",
                     "-o", "%(id)s.%(ext)s", url],
                    timeout=60,
                    stderr=subprocess.DEVNULL
                )
                candidates = []
                if vid:
                    candidates += [f"{vid}.{url_req.language}.vtt", f"{vid}.en.vtt", f"{vid}.en-US.vtt"]
                candidates += [p for p in os.listdir(".") if p.endswith(".vtt")]
                for candidate in candidates:
                    if os.path.exists(candidate):
                        vtt = candidate
                        break
            except subprocess.TimeoutExpired:
                logger.warning(f"yt-dlp download timeout for {url}")
                vtt = ""
            except Exception as yt_dl_exc:
                logger.warning(f"yt-dlp download failed for {url}: {yt_dl_exc}")
                vtt = ""
            if vtt:
                fallback_start = time.perf_counter()
                fallback_outcome = "success"
                try:
                    with RequestTimer(
                        "ingest_transcript_retry",
                        {"file": vtt, "user_id": user_id, "workspace_id": workspace_id},
                    ):
                        r = ingest_transcript(
                            vtt,
                            out_jsonl=CHUNKS_PATH,
                            language=url_req.language,
                            user_id=user_id,
                            workspace_id=workspace_id
                        )
                except Exception:
                    fallback_outcome = "failure"
                    raise
                finally:
                    INGEST_LATENCY.labels(
                        source="youtube",
                        outcome=fallback_outcome,
                    ).observe(max(time.perf_counter() - fallback_start, 0.0))
                results.append({"url": url, "written": r.get("written", 0), "mode": "auto_captions", "file": vtt})
                _log_event(
                    "ingest.youtube.completed",
                    url=url,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    api_key=bool(api_key_principal),
                    written=r.get("written", 0),
                    language=url_req.language,
                    mode="auto_captions",
                )
                _record_ingest_event("youtube", "success", 200)
                if r.get("written", 0):
                    INGEST_PROCESSED_CHUNKS.labels(source="youtube").inc(r.get("written", 0))
                total += r.get("written", 0)
            else:
                error_msg = "No transcript or auto-captions found. Video may not have subtitles available."
                results.append({"url": url, "error": error_msg, "written": 0})
                _log_event(
                    "ingest.youtube.failed",
                    url=url,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    api_key=bool(api_key_principal),
                    error=error_msg,
                    stage="fallback_unavailable",
                )
                _record_ingest_event("youtube", "failure", 404)
        finally:
            INGEST_LATENCY.labels(
                source="youtube",
                outcome=primary_outcome,
            ).observe(max(time.perf_counter() - start_time, 0.0))
    if total > 0:
        await _consume_workspace_quota(
            workspace_id,
            chunk_delta=total,
            current_chunk_total=current_chunk_total,
        )
    global _chunk_count_cache, _chunk_count_stamp
    _chunk_count_cache = None
    _chunk_count_stamp = None

    return {"results": results, "total_written": total, "count": _count_lines(CHUNKS_PATH)}

@app.post(
    "/api/ingest_files",
    summary="Upload and ingest documents",
    description="Upload multiple files (PDF, DOCX, Markdown, TXT, VTT, SRT) for ingestion. Requires write scope and active billing. Enforces workspace quotas. Rate limited to 10 uploads/hour.",
    tags=["Ingestion"]
)
@app.post("/ingest/files")
@limiter.limit("10/hour")
async def ingest_files(request: Request, files: List[UploadFile] = File(...), language: str = Form("en")):
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("write",),
        require=True,
    )
    user_id = user.get("user_id") if user else None
    await _require_billing_active(workspace_id)

    prepared_files, initial_results = await _prepare_file_payloads(files, user, workspace_id, api_key_principal)

    if not prepared_files and initial_results:
        # No files to process after validation
        return {"results": initial_results, "total_written": 0, "count": _count_lines(CHUNKS_PATH)}

    if BACKGROUND_JOBS_ENABLED and BACKGROUND_QUEUE and prepared_files:
        async def job_runner():
            return await _ingest_files_core(
                user,
                workspace_id,
                api_key_principal,
                prepared_files,
                language,
                initial_results,
            )

        job = BACKGROUND_QUEUE.submit(
            "ingest_files",
            job_runner,
            metadata={
                "workspace_id": workspace_id,
                "user_id": user_id,
                "language": language,
                "file_count": len(prepared_files),
            },
        )
        _log_event(
            "ingest.files.queued",
            workspace_id=workspace_id,
            user_id=user_id,
            job_id=job.id,
            language=language,
            file_count=len(prepared_files),
        )
        response: Dict[str, Any] = {"job_id": job.id, "queued": True, "status": "queued"}
        if initial_results:
            response["partial_results"] = initial_results
        return response

    return await _ingest_files_core(
        user,
        workspace_id,
        api_key_principal,
        prepared_files,
        language,
        initial_results,
    )

@app.post("/api/billing/checkout")
async def create_billing_checkout(request: Request, payload: BillingCheckoutRequest):
    if not BILLING_SERVICE:
        raise HTTPException(status_code=503, detail="Billing integration is not configured.")
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("write",),
        require=True,
    )
    require_admin(user, api_key_principal)
    organization_id = await _get_organization_id_for_workspace(workspace_id)
    if not organization_id:
        raise HTTPException(status_code=400, detail="Workspace organization not found.")

    try:
        session = await BILLING_SERVICE.create_checkout_session(
            organization_id,
            price_id=payload.price_id,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
        )
    except BillingServiceError as exc:
        _record_external_error("stripe", "checkout_session")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"id": session.get("id"), "url": session.get("url")}


@app.post("/api/billing/portal")
async def create_billing_portal(request: Request, payload: BillingPortalRequest):
    if not BILLING_SERVICE:
        raise HTTPException(status_code=503, detail="Billing integration is not configured.")
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("write",),
        require=True,
    )
    require_admin(user, api_key_principal)
    organization_id = await _get_organization_id_for_workspace(workspace_id)
    if not organization_id:
        raise HTTPException(status_code=400, detail="Workspace organization not found.")

    try:
        session = await BILLING_SERVICE.create_billing_portal_session(
            organization_id,
            return_url=payload.return_url,
        )
    except BillingServiceError as exc:
        _record_external_error("stripe", "billing_portal")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"id": session.get("id"), "url": session.get("url")}


@app.post("/api/billing/webhook")
async def stripe_webhook(request: Request):
    if not BILLING_SERVICE:
        raise HTTPException(status_code=503, detail="Billing integration is not configured.")
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")
    try:
        event = BILLING_SERVICE.construct_event(payload, signature)
        await BILLING_SERVICE.handle_event(event)
    except BillingServiceError as exc:
        _record_external_error("stripe", "webhook")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"received": True}


api_v1.post("/billing/checkout")(create_billing_checkout)
api_v1.post("/billing/portal")(create_billing_portal)
api_v1.post("/billing/webhook")(stripe_webhook)


def _require_admin_context(user: Optional[Dict[str, Any]], api_key: Optional[APIKeyPrincipal]) -> None:
    require_admin(user, api_key)


@api_v1.get("/admin/workspaces")
async def list_workspaces(request: Request):
    user, _, api_key_principal = await _resolve_auth_context(request, scopes=("admin",), require=True)
    _require_admin_context(user, api_key_principal)
    if DB is None:
        raise HTTPException(status_code=503, detail="Database not configured.")
    rows = await DB.fetch_all(
        """
        SELECT
            w.id,
            w.name,
            w.slug,
            w.organization_id,
            o.name AS organization_name,
            o.billing_status,
            o.plan,
            w.created_at,
            w.updated_at
        FROM workspaces w
        JOIN organizations o ON o.id = w.organization_id
        ORDER BY o.name, w.name
        """
    )
    return {"workspaces": rows}


@api_v1.get("/admin/billing")
async def list_billing_status(request: Request):
    user, _, api_key_principal = await _resolve_auth_context(request, scopes=("admin",), require=True)
    _require_admin_context(user, api_key_principal)
    if DB is None:
        raise HTTPException(status_code=503, detail="Database not configured.")
    rows = await DB.fetch_all(
        """
        SELECT
            id,
            name,
            billing_status,
            stripe_customer_id,
            stripe_subscription_id,
            plan,
            trial_ends_at,
            subscription_expires_at,
            billing_updated_at
        FROM organizations
        ORDER BY name
        """
    )
    return {"organizations": rows}


class BillingUpdate(BaseModel):
    plan: Optional[str] = None
    billing_status: Optional[str] = None
    trial_ends_at: Optional[datetime] = None
    subscription_expires_at: Optional[datetime] = None


@api_v1.patch("/admin/billing/{organization_id}")
async def update_billing_status(organization_id: str, payload: BillingUpdate, request: Request):
    user, _, api_key_principal = await _resolve_auth_context(request, scopes=("admin",), require=True)
    _require_admin_context(user, api_key_principal)
    if DB is None:
        raise HTTPException(status_code=503, detail="Database not configured.")
    fields = []
    values = []
    if payload.plan:
        fields.append("plan = $%d" % (len(values) + 1))
        values.append(payload.plan)
    if payload.billing_status:
        fields.append("billing_status = $%d" % (len(values) + 1))
        values.append(payload.billing_status)
    if payload.trial_ends_at is not None:
        fields.append("trial_ends_at = $%d" % (len(values) + 1))
        values.append(payload.trial_ends_at)
    if payload.subscription_expires_at is not None:
        fields.append("subscription_expires_at = $%d" % (len(values) + 1))
        values.append(payload.subscription_expires_at)
    if not fields:
        raise HTTPException(status_code=400, detail="No billing fields provided.")

    values.append(organization_id)
    query = f"""
    UPDATE organizations
    SET {', '.join(fields)}, billing_updated_at = NOW()
    WHERE id = ${len(values)}
    RETURNING *
    """
    row = await DB.fetch_one(query, tuple(values))
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return {"organization": row}


def _dedupe_chunks_sync() -> Dict[str, Any]:
    inp = CHUNKS_PATH
    tmp = CHUNKS_PATH + ".tmp"
    seen = set()
    kept = 0
    total = 0

    try:
        create_chunk_backup(CHUNKS_PATH)
    except ChunkBackupError as err:
        raise HTTPException(status_code=500, detail=f"Failed to backup chunks: {err}") from err

    try:
        with open(inp, "r", encoding="utf-8") as f, open(tmp, "w", encoding="utf-8") as g:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                k = obj.get("id") or json.dumps(obj, sort_keys=True)
                if k in seen:
                    continue
                seen.add(k)
                kept += 1
                g.write(json.dumps(obj, ensure_ascii=False) + "\n")
        os.replace(tmp, inp)
    except FileNotFoundError:
        pass
    except OSError as err:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to dedupe chunks: {err}") from err

    global _chunk_count_cache, _chunk_count_stamp
    _chunk_count_cache = None
    _chunk_count_stamp = None

    result = {"kept": kept, "total_before": total, "count": _count_lines(CHUNKS_PATH)}
    _log_event("chunks.dedupe.completed", kept=kept, total_before=total)
    return result


async def _run_dedupe_job() -> Dict[str, Any]:
    return await asyncio.to_thread(_dedupe_chunks_sync)


@app.post("/api/dedupe")
@app.post("/dedupe")
async def dedupe(request: Request):
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("write",),
        require=True,
    )
    if not user and not api_key_principal:
        raise HTTPException(status_code=401, detail="Authentication required.")

    if BACKGROUND_JOBS_ENABLED and BACKGROUND_QUEUE:
        job = BACKGROUND_QUEUE.submit(
            "dedupe",
            _run_dedupe_job,
            metadata={
                "workspace_id": workspace_id,
                "trigger": "api",
            },
        )
        _log_event("chunks.dedupe.queued", job_id=job.id, workspace_id=workspace_id)
        return {"job_id": job.id, "queued": True, "status": "queued"}

    result = await _run_dedupe_job()
    return result

api_v1.post("/dedupe")(dedupe)

@app.get(
    "/api/sources",
    summary="List ingested sources",
    description="Returns all document sources ingested by the authenticated user/workspace. Each source includes metadata like type, path, and chunk counts.",
    tags=["Sources"]
)
async def get_sources(request: Request):
    """List all unique sources with metadata (filtered by user)."""
    ensure_index()
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("read",),
        require=False,
    )
    user_id = user.get("user_id") if user else None
    if api_key_principal and user_id is None:
        user_id = api_key_principal.user_id
    sources = get_unique_sources(CHUNKS, user_id=user_id, workspace_id=workspace_id)
    return {"sources": sources, "count": len(sources)}
api_v1.get("/sources")(get_sources)

@app.get("/api/sources/{source_id}/chunks")
async def get_source_chunks(request: Request, source_id: str):
    """Get all chunks for a specific source (filtered by user)."""
    ensure_index()
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("read",),
        require=False,
    )
    user_id = user.get("user_id") if user else None
    if api_key_principal and user_id is None:
        user_id = api_key_principal.user_id
    chunks = get_chunks_by_source(CHUNKS, source_id, user_id=user_id, workspace_id=workspace_id)
    return {"chunks": chunks, "count": len(chunks)}
api_v1.get("/sources/{source_id}/chunks")(get_source_chunks)

@app.delete("/api/sources/{source_id}")
async def delete_source(request: Request, source_id: str):
    """Delete a source and all its chunks."""
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("write",),
        require=True,
    )
    user_id = user.get("user_id") if user else None
    if api_key_principal and user_id is None:
        user_id = api_key_principal.user_id

    global INDEX, CHUNKS
    result = delete_source_chunks(CHUNKS_PATH, source_id, workspace_id=workspace_id)
    INDEX = None
    CHUNKS = []
    global _chunk_count_cache, _chunk_count_stamp
    _chunk_count_cache = None
    _chunk_count_stamp = None
    return result
api_v1.delete("/sources/{source_id}")(delete_source)

@app.post(
    "/api/sources/batch_delete",
    summary="Batch delete multiple sources",
    description="Delete multiple sources and their chunks in one operation. Requires write scope. Returns count of deleted sources.",
    tags=["Sources"]
)
async def batch_delete_sources(request: Request, source_ids: List[str]):
    """Delete multiple sources at once."""
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("write",),
        require=True,
    )
    
    global INDEX, CHUNKS, _chunk_count_cache, _chunk_count_stamp
    
    deleted_count = 0
    total_kept = 0
    
    for source_id in source_ids:
        try:
            result = delete_source_chunks(CHUNKS_PATH, source_id, workspace_id=workspace_id)
            deleted_count += 1
            total_kept = result.get("kept", 0)
        except Exception as e:
            logger.error(f"Failed to delete source {source_id}: {e}")
    
    # Invalidate caches
    INDEX = None
    CHUNKS = []
    _chunk_count_cache = None
    _chunk_count_stamp = None
    
    return {
        "deleted": deleted_count,
        "failed": len(source_ids) - deleted_count,
        "kept": total_kept
    }

api_v1.post("/sources/batch_delete")(batch_delete_sources)

@app.get("/api/sources/{source_id}/preview")
async def get_source_preview(request: Request, source_id: str, limit: int = 3):
    """Get preview of a source (first few chunks, filtered by user)."""
    ensure_index()
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("read",),
        require=False,
    )
    user_id = user.get("user_id") if user else None
    if api_key_principal and user_id is None:
        user_id = api_key_principal.user_id
    chunks = get_chunks_by_source(CHUNKS, source_id, user_id=user_id, workspace_id=workspace_id)
    preview = chunks[:limit]
    return {"preview": preview, "total_chunks": len(chunks)}
api_v1.get("/sources/{source_id}/preview")(get_source_preview)

@app.get("/api/search")
async def search_source(request: Request, query: str, source_id: str = None, k: int = 8):
    """Search within all chunks or a specific source (filtered by user)."""
    ensure_index()
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("read",),
        require=False,
    )
    user_id = user.get("user_id") if user else None
    if api_key_principal and user_id is None:
        user_id = api_key_principal.user_id
    
    if source_id:
        source_chunks = get_chunks_by_source(CHUNKS, source_id, user_id=user_id, workspace_id=workspace_id)
        if not source_chunks:
            return {"chunks": [], "scores": []}
        temp_index = SimpleIndex(source_chunks)
        ranked = temp_index.search(query, k=k, user_id=user_id, workspace_id=workspace_id)
        results = [(source_chunks[i], score) for i, score in ranked]
    else:
        ranked = INDEX.search(query, k=k, user_id=user_id, workspace_id=workspace_id)
        results = [(CHUNKS[i], score) for i, score in ranked]
    
    chunks_with_scores = []
    for chunk, score in results:
        chunks_with_scores.append({
            "chunk": chunk,
            "score": float(score),
            "citation": format_citation(chunk)
        })
    return {"chunks": chunks_with_scores, "query": query}
api_v1.get("/search")(search_source)

@app.post("/api/rebuild")
@app.post("/rebuild")
async def rebuild_index(request: Request):
    """Rebuild the search index."""
    _, workspace_id, _ = await _resolve_auth_context(request, scopes=("write",), require=True)

    async def _run_rebuild() -> Dict[str, Any]:
        def _rebuild_sync() -> Dict[str, Any]:
            global INDEX, CHUNKS
            INDEX = None
            CHUNKS = []
            ensure_index()
            result = {"status": "rebuilt", "count": len(CHUNKS)}
            _log_event("index.rebuild.completed", count=result["count"], workspace_id=workspace_id)
            return result

        return await asyncio.to_thread(_rebuild_sync)

    if BACKGROUND_JOBS_ENABLED and BACKGROUND_QUEUE:
        job = BACKGROUND_QUEUE.submit(
            "rebuild_index",
            _run_rebuild,
            metadata={"workspace_id": workspace_id},
        )
        _log_event("index.rebuild.queued", job_id=job.id, workspace_id=workspace_id)
        return {"job_id": job.id, "queued": True, "status": "queued"}

    return await _run_rebuild()
api_v1.post("/rebuild")(rebuild_index)

# Admin-only endpoints
@app.get("/api/admin/users")
async def list_users(request: Request):
    """List all users (admin only)."""
    user, _, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("admin",),
        require=True,
    )
    require_admin(user, api_key_principal)
    
    if not USER_SERVICE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. User management requires database connection."
        )
    
    users = await USER_SERVICE.list_all_users()
    return {"users": users, "count": len(users)}
api_v1.get("/admin/users")(list_users)

@app.patch("/api/admin/users/{user_id}/role")
async def update_user_role(request: Request, user_id: str, role: str = Form(...)):
    """Update a user's role (admin only)."""
    user, _, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("admin",),
        require=True,
    )
    require_admin(user, api_key_principal)
    
    if not USER_SERVICE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. User management requires database connection."
        )
    
    # Validate role
    valid_roles = ['admin', 'editor', 'reader', 'owner']
    if role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )
    
    updated_user = await USER_SERVICE.update_user_role(user_id, role)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"user": updated_user, "message": f"User role updated to {role}"}
api_v1.patch("/admin/users/{user_id}/role")(update_user_role)

@app.get("/api/admin/stats")
async def admin_stats(request: Request):
    """Get system-wide statistics (admin only)."""
    user, _, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("admin",),
        require=True,
    )
    require_admin(user, api_key_principal)

    ensure_index()
    
    # Count chunks by user
    user_chunks = {}
    total_chunks = len(CHUNKS)
    for chunk in CHUNKS:
        uid = chunk.get('user_id', 'legacy')
        user_chunks[uid] = user_chunks.get(uid, 0) + 1
    
    # Count sources
    sources = get_unique_sources(CHUNKS)
    
    return {
        "total_chunks": total_chunks,
        "chunks_by_user": user_chunks,
        "total_sources": len(sources),
        "database_available": DB is not None,
        "auth_available": AUTH_AVAILABLE
    }
api_v1.get("/admin/stats")(admin_stats)

@api_v1.get("/admin/audit")
async def list_audit_events(request: Request, limit: int = 100):
    user, _, api_key_principal = await _resolve_auth_context(request, scopes=("admin",), require=True)
    _require_admin_context(user, api_key_principal)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="limit must be an integer")
    events = _read_audit_events(limit)
    return {"events": events}

app.include_router(api_v1)
api_v1.get("/admin/stats")(admin_stats)

def _read_audit_events(limit: int) -> List[Dict[str, Any]]:
    if not os.path.exists(AUDIT_LOG_PATH):
        return []
    try:
        limit = max(1, min(limit, 500))
    except Exception:
        limit = 100
    lines: deque[str] = deque(maxlen=limit)
    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            entry = line.strip()
            if entry:
                lines.append(entry)
    events: List[Dict[str, Any]] = []
    for entry in lines:
        try:
            events.append(json.loads(entry))
        except json.JSONDecodeError:
            continue
    return events

async def _prepare_file_payloads(
    files: List[UploadFile],
    user: Optional[Dict[str, Any]],
    workspace_id: Optional[str],
    api_key_principal: Optional[APIKeyPrincipal],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    prepared: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    user_id = user.get("user_id") if user else None

    for upload in files:
        if upload is None or not upload.filename:
            continue

        if not validate_file_type(upload.filename):
            results.append(
                {
                    "file": upload.filename,
                    "error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
                }
            )
            _log_event(
                "ingest.file.skipped",
                file=upload.filename,
                reason="unsupported_type",
                user_id=user_id,
                workspace_id=workspace_id,
                api_key=bool(api_key_principal),
            )
            _record_ingest_event("file", "skipped", 400)
            continue

        safe_name = generate_safe_filename(upload.filename)
        size = 0
        content = bytearray()
        try:
            while True:
                chunk = await upload.read(8192)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    results.append(
                        {
                            "file": upload.filename,
                            "error": f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)}MB",
                        }
                    )
                    _log_event(
                        "ingest.file.failed",
                        file=upload.filename,
                        safe_name=safe_name,
                        reason="size_limit",
                        size=size,
                        user_id=user_id,
                        workspace_id=workspace_id,
                        api_key=bool(api_key_principal),
                    )
                    _record_ingest_event("file", "failure", 400)
                    break
                content.extend(chunk)
        except Exception as exc:
            results.append({"file": upload.filename, "error": f"Failed to read file: {exc}"})
            _log_event(
                "ingest.file.failed",
                file=upload.filename,
                safe_name=safe_name,
                reason="read_error",
                error=str(exc),
                user_id=user_id,
                workspace_id=workspace_id,
                api_key=bool(api_key_principal),
            )
            _record_ingest_event("file", "failure", 500)
            continue
        finally:
            try:
                await upload.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass

        if size > MAX_FILE_SIZE:
            continue

        prepared.append(
            {
                "file": upload.filename,
                "safe_name": safe_name,
                "content": bytes(content),
            }
        )

    return prepared, results


async def _ingest_files_core(
    user: Optional[Dict[str, Any]],
    workspace_id: Optional[str],
    api_key_principal: Optional[APIKeyPrincipal],
    prepared_files: List[Dict[str, Any]],
    language: str,
    initial_results: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = list(initial_results or [])
    total = 0
    user_id = user.get("user_id") if user else None

    await _consume_workspace_quota(workspace_id, request_delta=1)
    current_chunk_total = await _count_workspace_chunks(workspace_id)

    UPLOAD_DIR.mkdir(exist_ok=True)

    for payload in prepared_files:
        safe_name = payload["safe_name"]
        original = payload["file"]
        path = UPLOAD_DIR / safe_name

        try:
            with open(path, "wb") as out_file:
                out_file.write(payload["content"])
        except Exception as exc:
            results.append({"file": original, "error": f"Failed to save file: {exc}"})
            _log_event(
                "ingest.file.failed",
                file=original,
                safe_name=safe_name,
                reason="save_error",
                error=str(exc),
                user_id=user_id,
                workspace_id=workspace_id,
                api_key=bool(api_key_principal),
            )
            _record_ingest_event("file", "failure", 500)
            continue

        lower = safe_name.lower()
        handler = "unknown"
        processing_start = time.perf_counter()
        processing_outcome = "success"
        record: Dict[str, Any] = {}
        try:
            with RequestTimer(
                "ingest_file",
                {"file": safe_name, "user_id": user_id, "workspace_id": workspace_id, "api_key": bool(api_key_principal)},
            ):
                if lower.endswith((".vtt", ".srt", ".txt")):
                    handler = "transcript"
                    record = ingest_transcript(
                        str(path),
                        out_jsonl=CHUNKS_PATH,
                        language=language,
                        user_id=user_id,
                        workspace_id=workspace_id,
                    )
                elif lower.endswith((".pdf", ".docx", ".md", ".markdown")):
                    handler = "docs"
                    record = ingest_docs(
                        str(path),
                        out_jsonl=CHUNKS_PATH,
                        language=language,
                        user_id=user_id,
                        workspace_id=workspace_id,
                    )
                else:
                    record = {"error": "unsupported file type"}
        except Exception as exc:
            record = {"error": str(exc)}
            processing_outcome = "failure"
        else:
            if record.get("error"):
                processing_outcome = "failure"
        finally:
            INGEST_LATENCY.labels(source="file", outcome=processing_outcome).observe(
                max(time.perf_counter() - processing_start, 0.0)
            )

        written_count = int(record.get("written", 0) or 0)
        results.append({"file": original, "safe_name": safe_name, **record})
        total += written_count
        status = "failed" if record.get("error") else "completed"
        _log_event(
            f"ingest.file.{status}",
            file=original,
            safe_name=safe_name,
            handler=handler,
            written=written_count,
            language=language,
            user_id=user_id,
            workspace_id=workspace_id,
            api_key=bool(api_key_principal),
            error=record.get("error"),
        )
        if record.get("error"):
            _record_ingest_event("file", "failure", 500)
        else:
            _record_ingest_event("file", "success", 200)
            if written_count:
                INGEST_PROCESSED_CHUNKS.labels(source="file").inc(written_count)

    if total > 0:
        await _consume_workspace_quota(
            workspace_id,
            chunk_delta=total,
            current_chunk_total=current_chunk_total,
        )
    global _chunk_count_cache, _chunk_count_stamp
    _chunk_count_cache = None
    _chunk_count_stamp = None

    return {"results": results, "total_written": total, "count": _count_lines(CHUNKS_PATH)}
