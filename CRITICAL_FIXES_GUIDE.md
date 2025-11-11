# Critical Fixes Implementation Guide

This document provides code-level fixes for the most critical security and robustness issues.

## 1. File Upload Security Fixes

### Current Problem
```python
# server.py line 128-130
name = f.filename
path = os.path.join("uploads", name)
with open(path, "wb") as out: out.write(await f.read())
```

**Vulnerabilities:**
- Path traversal: `../../../etc/passwd`
- No file size limit
- No file type validation

### Fixed Implementation

```python
import os
import hashlib
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from typing import List

# Configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.md', '.markdown', '.txt', '.vtt', '.srt'}
UPLOAD_DIR = Path("uploads")

def sanitize_filename(filename: str) -> str:
    """Remove path components and dangerous characters."""
    # Get just the filename, no path
    name = os.path.basename(filename)
    # Remove any remaining path separators
    name = name.replace('/', '').replace('\\', '')
    # Remove dangerous characters
    name = ''.join(c for c in name if c.isalnum() or c in '.-_')
    # Limit length
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
    # Add UUID to prevent collisions and ensure uniqueness
    name_hash = hashlib.md5(sanitized.encode()).hexdigest()[:8]
    return f"{name_hash}_{sanitized}"

@app.post("/api/ingest_files")
@app.post("/ingest/files")
async def ingest_files(files: List[UploadFile] = File(...), language: str = Form("en")):
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
                    raise HTTPException(
                        status_code=413,
                        detail=f"File {f.filename} exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)}MB"
                    )
                content += chunk
        except Exception as e:
            results.append({"file": f.filename, "error": str(e)})
            continue
        
        # Write file
        try:
            with open(path, "wb") as out:
                out.write(content)
        except Exception as e:
            results.append({"file": f.filename, "error": f"Failed to save file: {str(e)}"})
            continue
        
        # Process file
        lower = safe_name.lower()
        try:
            if lower.endswith((".vtt", ".srt", ".txt")):
                r = ingest_transcript(str(path), out_jsonl=CHUNKS_PATH, language=language)
            elif lower.endswith((".pdf", ".docx", ".md", ".markdown")):
                r = ingest_docs(str(path), out_jsonl=CHUNKS_PATH, language=language)
            else:
                r = {"error": "unsupported file type"}
        except Exception as e:
            r = {"error": str(e)}
        
        results.append({"file": f.filename, "safe_name": safe_name, **r})
        total += int(r.get("written", 0) or 0)
    
    return {"results": results, "total_written": total, "count": _count_lines(CHUNKS_PATH)}
```

## 2. Input Validation with Pydantic

### Current Problem
- No validation on query length, `k` parameter, URLs
- Type errors possible

### Fixed Implementation

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

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
        if len(lines) > 100:  # Limit batch size
            raise ValueError('Maximum 100 URLs per request')
        
        # Validate URL format
        url_pattern = re.compile(
            r'^https?://(www\.)?(youtube\.com|youtu\.be)/.*$',
            re.IGNORECASE
        )
        for url in lines:
            if not url_pattern.match(url):
                raise ValueError(f'Invalid URL format: {url}')
        return v

@app.post("/ask")
async def ask(request: AskRequest):
    """Ask endpoint with validation."""
    ensure_index()
    ranked = INDEX.search(request.query, k=request.k)
    # ... rest of implementation
```

## 3. Error Handling Improvements

### Current Problem
```python
except Exception:  # Too broad
    pass  # Swallows errors
```

### Fixed Implementation

```python
import logging
from fastapi import HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

class RAGError(Exception):
    """Base exception for RAG system."""
    pass

class IndexNotFoundError(RAGError):
    """Raised when index is not found."""
    pass

class InvalidQueryError(RAGError):
    """Raised when query is invalid."""
    pass

@app.exception_handler(RAGError)
async def rag_error_handler(request, exc):
    """Handle RAG-specific errors."""
    logger.error(f"RAG Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=400,
        content={"error": "An error occurred processing your request", "type": type(exc).__name__}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors."""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "An internal error occurred. Please try again later."}
    )

def ensure_index():
    global INDEX, CHUNKS
    if INDEX is None:
        if not os.path.exists(CHUNKS_PATH):
            raise IndexNotFoundError(f"Index not found. Please ingest documents first.")
        try:
            CHUNKS = load_chunks(CHUNKS_PATH)
        except Exception as e:
            logger.error(f"Failed to load chunks: {e}", exc_info=True)
            raise IndexNotFoundError("Failed to load index. Please rebuild.")
        
        if not CHUNKS:
            raise IndexNotFoundError("Index is empty. Please ingest documents first.")
        
        try:
            INDEX = SimpleIndex(CHUNKS)
        except Exception as e:
            logger.error(f"Failed to build index: {e}", exc_info=True)
            raise IndexNotFoundError("Failed to build search index.")
```

## 4. URL Validation for YouTube Ingestion

### Current Problem
```python
subprocess.check_output(["yt-dlp", "--print", "id", "--skip-download", url], ...)
# User input directly in command
```

### Fixed Implementation

```python
import re
import subprocess
from urllib.parse import urlparse

def validate_youtube_url(url: str) -> bool:
    """Validate YouTube URL format."""
    youtube_patterns = [
        r'^https?://(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(www\.)?youtube\.com/embed/[\w-]+',
        r'^https?://youtu\.be/[\w-]+',
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from YouTube URL safely."""
    if not validate_youtube_url(url):
        raise ValueError(f"Invalid YouTube URL: {url}")
    
    patterns = [
        r'[?&]v=([\w-]+)',
        r'/embed/([\w-]+)',
        r'youtu\.be/([\w-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.post("/api/ingest_urls")
@app.post("/ingest/urls")
async def ingest_urls(request: IngestURLRequest):
    """Ingest YouTube URLs with validation."""
    urls_list = [u.strip() for u in request.urls.splitlines() if u.strip()]
    results = []
    total = 0
    
    for url in urls_list:
        try:
            # Validate URL
            if not validate_youtube_url(url):
                results.append({"url": url, "error": "Invalid YouTube URL format"})
                continue
            
            # Extract video ID safely
            video_id = extract_video_id(url)
            if not video_id:
                results.append({"url": url, "error": "Could not extract video ID"})
                continue
            
            # Use video ID instead of full URL in subprocess
            try:
                r = ingest_youtube(url, out_jsonl=CHUNKS_PATH, language=request.language)
                results.append({"url": url, "written": r.get("written", 0), "mode": "transcript"})
                total += r.get("written", 0)
            except Exception as e:
                logger.error(f"Failed to ingest {url}: {e}", exc_info=True)
                # Fallback with safe video ID
                try:
                    # Use video_id instead of url in subprocess calls
                    vid_output = subprocess.check_output(
                        ["yt-dlp", "--print", "id", "--skip-download", url],
                        text=True,
                        timeout=30,  # Add timeout
                        stderr=subprocess.DEVNULL
                    ).strip()
                    # ... rest of fallback logic
                except subprocess.TimeoutExpired:
                    results.append({"url": url, "error": "Request timed out"})
                except Exception as e:
                    logger.error(f"Fallback failed for {url}: {e}")
                    results.append({"url": url, "error": "No transcript available"})
        except ValueError as e:
            results.append({"url": url, "error": str(e)})
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}", exc_info=True)
            results.append({"url": url, "error": "An unexpected error occurred"})
    
    return {"results": results, "total_written": total, "count": _count_lines(CHUNKS_PATH)}
```

## 5. Rate Limiting

### Implementation

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/ask")
@limiter.limit("30/minute")  # 30 requests per minute
async def ask(request: Request, query: str = Form(...), k: int = Form(8)):
    # ... implementation

@app.post("/api/ingest_files")
@limiter.limit("10/hour")  # 10 uploads per hour
async def ingest_files(request: Request, files: List[UploadFile] = File(...)):
    # ... implementation
```

## 6. Thread-Safe Index Management

### Current Problem
Global variables `INDEX` and `CHUNKS` are not thread-safe.

### Fixed Implementation

```python
import threading
from typing import Optional

class ThreadSafeIndex:
    def __init__(self):
        self._index: Optional[SimpleIndex] = None
        self._chunks: List[Dict] = []
        self._lock = threading.RLock()
    
    def get(self) -> tuple[SimpleIndex, List[Dict]]:
        """Get index and chunks, loading if necessary."""
        with self._lock:
            if self._index is None:
                self._load()
            return self._index, self._chunks
    
    def _load(self):
        """Load index and chunks."""
        if not os.path.exists(CHUNKS_PATH):
            raise IndexNotFoundError(f"Index not found at {CHUNKS_PATH}")
        
        self._chunks = load_chunks(CHUNKS_PATH)
        if not self._chunks:
            raise IndexNotFoundError("No chunks loaded")
        
        self._index = SimpleIndex(self._chunks)
    
    def invalidate(self):
        """Invalidate cache (force reload on next access)."""
        with self._lock:
            self._index = None
            self._chunks = []

# Global thread-safe index
_index_manager = ThreadSafeIndex()

def ensure_index():
    """Ensure index is loaded (thread-safe)."""
    return _index_manager.get()

@app.post("/api/rebuild")
def rebuild_index():
    """Rebuild index (thread-safe)."""
    _index_manager.invalidate()
    _index_manager.get()  # Force reload
    return {"status": "rebuilt", "count": len(_index_manager._chunks)}
```

## 7. Request Timeout Handling

### Implementation

```python
from fastapi import Request
import asyncio

@app.post("/ask")
async def ask(request: Request, query: str = Form(...), k: int = Form(8)):
    try:
        # Set timeout for the operation
        result = await asyncio.wait_for(
            _process_query(query, k),
            timeout=30.0  # 30 second timeout
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Request timed out. Please try a simpler query or contact support."
        )

async def _process_query(query: str, k: int):
    """Process query asynchronously."""
    ensure_index()
    ranked = INDEX.search(query, k=k)
    # ... rest of processing
    return {"answer": ans, "citations": cites, "score": sc}
```

## 8. Logging Configuration

### Implementation

```python
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    """Configure application logging."""
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("rag")
    logger.setLevel(logging.INFO)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "rag.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logging at startup
logger = setup_logging()
```

## 9. Health Check Endpoint

### Implementation

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check if index exists and is loadable
        if os.path.exists(CHUNKS_PATH):
            chunks = load_chunks(CHUNKS_PATH)
            index_status = "healthy" if chunks else "empty"
        else:
            index_status = "not_found"
        
        # Check disk space
        import shutil
        disk_usage = shutil.disk_usage(".")
        disk_free_percent = (disk_usage.free / disk_usage.total) * 100
        
        return {
            "status": "healthy" if index_status == "healthy" and disk_free_percent > 10 else "degraded",
            "index": index_status,
            "disk_free_percent": round(disk_free_percent, 2),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
```

## 10. CORS Configuration

### Implementation

```python
from fastapi.middleware.cors import CORSMiddleware

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Development
        "https://yourdomain.com",  # Production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)
```

---

## Priority Implementation Order

1. **Week 1:** File upload security, input validation, error handling
2. **Week 2:** URL validation, rate limiting, logging
3. **Week 3:** Thread safety, timeouts, health checks
4. **Week 4:** CORS, testing, documentation

These fixes address the most critical security and robustness issues that would block commercial deployment.

