
import os, json, subprocess, hashlib, re, logging, asyncio, time
from typing import List, Optional, Dict, Any, Sequence, Tuple
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

from retrieval import load_chunks, SimpleIndex, format_citation, get_unique_sources, get_chunks_by_source, delete_source_chunks
from score import score_answer
# Import ingestion functions directly from raglite for user_id support
from raglite import ingest_youtube, ingest_transcript, ingest_docs

from api_key_service import ApiKeyService
from api_key_auth import configure_api_key_auth, get_api_key_principal, APIKeyPrincipal

from chunk_backup import ChunkBackupError, create_chunk_backup

from logging_utils import configure_logging
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
import httpx

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

CHUNKS_PATH = os.environ.get("CHUNKS_PATH", "out/chunks.jsonl")
INDEX = None
CHUNKS = []
_chunk_count_cache: Optional[int] = None
_chunk_count_stamp: Optional[float] = None
API_DESCRIPTION = (
    "RAG Talking Agent backend.\n\n"
    "Versioned REST endpoints are available under `/api/v1`. "
    "Authentication supports Google OAuth JWTs and API keys (set `X-API-Key`)."
)

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
            "default-src 'self'; frame-ancestors 'none'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'",
        )
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Content-Security-Policy", csp)
        return response


app.add_middleware(SecurityHeadersMiddleware)


# Prometheus metrics for request/ingest observability
ASK_REQUEST_COUNTER = Counter(
    "ask_requests_total",
    "Total number of ask requests handled.",
    ["outcome"],
)
ASK_LATENCY = Histogram(
    "ask_request_latency_seconds",
    "Latency of ask requests in seconds.",
    ["outcome"],
)
INGEST_COUNTER = Counter(
    "ingest_operations_total",
    "Total ingest operations processed (server-side).",
    ["source", "outcome"],
)
INGEST_LATENCY = Histogram(
    "ingest_operation_latency_seconds",
    "Latency of ingest operations in seconds.",
    ["source", "outcome"],
)
CHUNK_COUNT_GAUGE = Gauge(
    "chunk_records_total",
    "Current number of chunk records available to the search index.",
)

# Session middleware (required for OAuth)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-this-secret-key-in-production"))

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


app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

# Setup logging
logger = configure_logging()

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
    logger.info(event, extra=payload)


async def _ping_healthchecks(success: bool, payload: Dict[str, Any]) -> None:
    """Send uptime pings to Healthchecks or similar services when configured."""
    if not HEALTHCHECKS_PING_URL:
        return

    url = HEALTHCHECKS_PING_URL if success else (HEALTHCHECKS_PING_FAIL_URL or f"{HEALTHCHECKS_PING_URL}/fail")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json=payload)
    except Exception as exc:
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
        return user, workspace_id, api_key_principal

    user = get_current_user(request)
    if require and not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Supply an API key or sign in via Google OAuth.",
        )
    workspace_id = await _get_primary_workspace_id_for_user(user)
    return user, workspace_id, None


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

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup (if configured)."""
    global DB, USER_SERVICE, API_KEY_SERVICE
    
    # Try to initialize database if connection string is provided
    db_url = os.environ.get("DATABASE_URL")
    if db_url and DATABASE_AVAILABLE:
        try:
            DB = await init_database(db_url, init_schema=False)
            USER_SERVICE = get_user_service(DB)
            API_KEY_SERVICE = ApiKeyService(DB)
            configure_api_key_auth(API_KEY_SERVICE)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize database: {e}")
            logger.warning("Server will run without database features")
            DB = None
            USER_SERVICE = None
            API_KEY_SERVICE = None
            configure_api_key_auth(None)
    else:
        logger.info("No DATABASE_URL configured - running without database")
        configure_api_key_auth(None)
    asyncio.create_task(_warm_and_measure())

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    global DB
    if DB:
        # Database cleanup if needed
        logger.info("Shutting down database connection")

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
                    resp = await client.get(
                        "https://www.googleapis.com/oauth2/v2/userinfo",
                        headers={"Authorization": f"Bearer {access_token}"},
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
    user, workspace_id, api_key = await _resolve_auth_context(request, scopes=("read",), require=False)
    if user or api_key:
        return {
            "authenticated": True,
            "user": user,
            "workspace_id": workspace_id,
            "via_api_key": api_key is not None,
        }
    return {"authenticated": False}

@app.post("/ask")
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

    # Add timeout for query processing
    import asyncio
    start_time = asyncio.get_event_loop().time()
    outcome = "success"
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
        raise HTTPException(
            status_code=504,
            detail="Request timed out. Please try a simpler query or contact support."
        )
    except HTTPException:
        outcome = "error"
        raise
    except Exception:
        outcome = "error"
        raise
    finally:
        duration = asyncio.get_event_loop().time() - start_time
        ASK_REQUEST_COUNTER.labels(outcome=outcome).inc()
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

@app.get("/api/stats")
def stats():
    return {"count": _count_lines(CHUNKS_PATH)}
api_v1.get("/stats")(stats)

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

    # Validate input
    try:
        url_req = IngestURLRequest(urls=urls, language=language)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    urls_list = [u.strip() for u in url_req.urls.splitlines() if u.strip()]
    results = []
    total = 0
    
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
            INGEST_COUNTER.labels(source="youtube", outcome="skipped").inc()
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
                INGEST_COUNTER.labels(source="youtube", outcome="failure").inc()
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
                INGEST_COUNTER.labels(source="youtube", outcome="success").inc()
            total += written
        except Exception as e:
            logger.error(f"Error ingesting YouTube URL {url}: {e}", exc_info=True)
            _log_event(
                "ingest.youtube.failed",
                url=url,
                user_id=user_id,
                workspace_id=workspace_id,
                api_key=bool(api_key_principal),
                error=str(e),
                stage="primary_exception",
            )
            INGEST_COUNTER.labels(source="youtube", outcome="failure").inc()
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
            except Exception as e:
                logger.warning(f"yt-dlp failed for {url}: {e}")
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
                for c in candidates:
                    if os.path.exists(c):
                        vtt = c; break
            except subprocess.TimeoutExpired:
                logger.warning(f"yt-dlp download timeout for {url}")
                vtt = ""
            except Exception as e:
                logger.warning(f"yt-dlp download failed for {url}: {e}")
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
                results.append({"url": url, "written": r.get("written",0), "mode": "auto_captions", "file": vtt})
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
                INGEST_COUNTER.labels(source="youtube", outcome="success").inc()
                total += r.get("written",0)
            else:
                error_msg = f"No transcript or auto-captions found. Video may not have subtitles available."
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
                INGEST_COUNTER.labels(source="youtube", outcome="failure").inc()
        finally:
            INGEST_LATENCY.labels(
                source="youtube",
                outcome=primary_outcome,
            ).observe(max(time.perf_counter() - start_time, 0.0))
    global _chunk_count_cache, _chunk_count_stamp
    _chunk_count_cache = None
    _chunk_count_stamp = None

    return {"results": results, "total_written": total, "count": _count_lines(CHUNKS_PATH)}
api_v1.post("/ingest/urls")(ingest_urls)

@app.post("/api/ingest_files")
@app.post("/ingest/files")
@limiter.limit("10/hour")
async def ingest_files(request: Request, files: List[UploadFile] = File(...), language: str = Form("en")):
    user, workspace_id, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("write",),
        require=True,
    )
    user_id = user.get("user_id") if user else None

    UPLOAD_DIR.mkdir(exist_ok=True)
    results = []
    total = 0
    
    for f in files:
        # Validate file type
        if not validate_file_type(f.filename):
            results.append({
                "file": f.filename,
                "error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            })
            _log_event(
                "ingest.file.skipped",
                file=f.filename,
                reason="unsupported_type",
                user_id=user_id,
                workspace_id=workspace_id,
                api_key=bool(api_key_principal),
            )
            INGEST_COUNTER.labels(source="file", outcome="skipped").inc()
            continue
        
        # Generate safe filename
        safe_name = generate_safe_filename(f.filename)
        path = UPLOAD_DIR / safe_name
        
        # Read file with size limit
        content = b""
        size = 0
        try:
            while True:
                chunk = await f.read(8192)  # 8KB chunks
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    results.append({
                        "file": f.filename,
                        "error": f"File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)}MB"
                    })
                    _log_event(
                        "ingest.file.failed",
                        file=f.filename,
                        safe_name=safe_name,
                        reason="size_limit",
                        size=size,
                        user_id=user_id,
                        workspace_id=workspace_id,
                        api_key=bool(api_key_principal),
                    )
                    INGEST_COUNTER.labels(source="file", outcome="failure").inc()
                    break
                content += chunk
        except Exception as e:
            results.append({"file": f.filename, "error": f"Failed to read file: {str(e)}"})
            _log_event(
                "ingest.file.failed",
                file=f.filename,
                safe_name=safe_name,
                reason="read_error",
                error=str(e),
                user_id=user_id,
                workspace_id=workspace_id,
                api_key=bool(api_key_principal),
            )
            INGEST_COUNTER.labels(source="file", outcome="failure").inc()
            continue
        
        if size > MAX_FILE_SIZE:
            continue
        
        # Write file
        try:
            with open(path, "wb") as out:
                out.write(content)
        except Exception as e:
            results.append({"file": f.filename, "error": f"Failed to save file: {str(e)}"})
            _log_event(
                "ingest.file.failed",
                file=f.filename,
                safe_name=safe_name,
                reason="save_error",
                error=str(e),
                user_id=user_id,
                workspace_id=workspace_id,
                api_key=bool(api_key_principal),
            )
            INGEST_COUNTER.labels(source="file", outcome="failure").inc()
            continue
        
        # Process file
        lower = safe_name.lower()
        handler = "unknown"
        processing_start = time.perf_counter()
        processing_outcome = "success"
        r: Dict[str, Any] = {}
        try:
            with RequestTimer(
                "ingest_file",
                {"file": safe_name, "user_id": user_id, "workspace_id": workspace_id, "api_key": bool(api_key_principal)},
            ):
                if lower.endswith((".vtt", ".srt", ".txt")):
                    handler = "transcript"
                    r = ingest_transcript(
                        str(path),
                        out_jsonl=CHUNKS_PATH,
                        language=language,
                        user_id=user_id,
                        workspace_id=workspace_id
                    )
                elif lower.endswith((".pdf", ".docx", ".md", ".markdown")):
                    handler = "docs"
                    r = ingest_docs(
                        str(path),
                        out_jsonl=CHUNKS_PATH,
                        language=language,
                        user_id=user_id,
                        workspace_id=workspace_id
                    )
                else:
                    r = {"error": "unsupported file type"}
        except Exception as e:
            r = {"error": str(e)}
            processing_outcome = "failure"
        else:
            if r.get("error"):
                processing_outcome = "failure"
        finally:
            INGEST_LATENCY.labels(
                source="file",
                outcome=processing_outcome,
            ).observe(max(time.perf_counter() - processing_start, 0.0))
        
        results.append({"file": f.filename, "safe_name": safe_name, **r})
        total += int(r.get("written", 0) or 0)
        status = "failed" if r.get("error") else "completed"
        _log_event(
            f"ingest.file.{status}",
            file=f.filename,
            safe_name=safe_name,
            handler=handler,
            written=int(r.get("written", 0) or 0),
            language=language,
            user_id=user_id,
            workspace_id=workspace_id,
            api_key=bool(api_key_principal),
            error=r.get("error"),
        )
        INGEST_COUNTER.labels(
            source="file",
            outcome="failure" if r.get("error") else "success",
        ).inc()
    
    global _chunk_count_cache, _chunk_count_stamp
    _chunk_count_cache = None
    _chunk_count_stamp = None

    return {"results": results, "total_written": total, "count": _count_lines(CHUNKS_PATH)}
api_v1.post("/ingest/files")(ingest_files)

@app.post("/api/dedupe")
@app.post("/dedupe")
async def dedupe(request: Request):
    user, _, api_key_principal = await _resolve_auth_context(
        request,
        scopes=("write",),
        require=True,
    )
    # API key already validated; JWT path ensures user exists.
    if not user and not api_key_principal:
        raise HTTPException(status_code=401, detail="Authentication required.")

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

    return {"kept": kept, "total_before": total, "count": _count_lines(CHUNKS_PATH)}
api_v1.post("/dedupe")(dedupe)

@app.get("/api/sources")
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
    await _resolve_auth_context(request, scopes=("write",), require=True)

    global INDEX, CHUNKS
    INDEX = None
    CHUNKS = []
    ensure_index()
    return {"status": "rebuilt", "count": len(CHUNKS)}
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

app.include_router(api_v1)
api_v1.get("/admin/stats")(admin_stats)
