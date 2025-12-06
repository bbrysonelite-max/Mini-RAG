"""
Database-backed ingestion functions.

Modified versions of raglite.py functions that store chunks directly to PostgreSQL
instead of JSONL files.
"""

import os
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

# Import original parsing functions from raglite
from raglite import (
    parse_srt,
    parse_vtt,
    chunk_timecoded,
    read_pdf,
    read_docx,
    read_image,
    read_text,
    fetch_youtube_transcript,
    _extract_video_id
)

from chunk_db import store_chunks_to_db, generate_chunk_id

logger = logging.getLogger(__name__)


async def ingest_transcript_db(
    path: str,
    vector_store,
    language: str = "en",
    user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    context: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Ingest transcript file directly to database.
    
    Args:
        path: Path to transcript file (.srt, .vtt, or plain text)
        vector_store: VectorStore instance for database access
        language: Language code
        user_id: Optional user ID
        workspace_id: Optional workspace ID
        context: Optional database context
        
    Returns:
        Dictionary with ingestion results
    """
    ext = os.path.splitext(path)[1].lower()
    
    # Parse transcript based on format
    if ext == ".srt":
        parts = parse_srt(path)
    elif ext == ".vtt":
        parts = parse_vtt(path)
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read().strip()
        parts = [(0.0, 0.0, txt)]
    
    # Create chunks
    chunks = chunk_timecoded(parts, 1200, 150)
    rows = []
    
    for idx, (start, end, text) in enumerate(chunks):
        chunk = {
            "id": generate_chunk_id(
                text,
                {"type": "transcript", "path": path},
                {"chunk_index": idx, "start_sec": start}
            ),
            "content": text,
            "source": {
                "type": "transcript",
                "path": path
            },
            "metadata": {
                "chunk_index": idx,
                "start_sec": start,
                "end_sec": end,
                "language": language,
                "created_at": datetime.now().isoformat()
            }
        }
        
        if user_id:
            chunk["user_id"] = user_id
        if workspace_id:
            chunk["workspace_id"] = workspace_id
        
        rows.append(chunk)
    
    # Store to database
    if not context:
        context = await vector_store.ensure_default_context()
    
    result = await store_chunks_to_db(rows, vector_store, context)
    result["path"] = path
    result["type"] = "transcript"
    
    return result


async def ingest_docs_db(
    path: str,
    vector_store,
    language: str = "en",
    user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    context: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Ingest document file directly to database.
    
    Args:
        path: Path to document file (PDF, DOCX, image, or text)
        vector_store: VectorStore instance for database access
        language: Language code
        user_id: Optional user ID
        workspace_id: Optional workspace ID
        context: Optional database context
        
    Returns:
        Dictionary with ingestion results
    """
    ext = os.path.splitext(path)[1].lower()
    
    # Read document based on format
    if ext == ".pdf":
        text = read_pdf(path)
    elif ext == ".docx":
        text = read_docx(path)
    elif ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}:
        text = read_image(path)
    else:
        # Treat everything else as text (markdown, txt, etc.)
        text = read_text(path)
    
    # Simple chunking for documents
    rows = []
    chunk_size = 1200
    overlap = 150
    
    if not text:
        return {"written": 0, "path": path, "type": "document", "storage": "database"}
    
    # Create overlapping chunks
    text_length = len(text)
    chunk_starts = []
    pos = 0
    
    while pos < text_length:
        chunk_starts.append(pos)
        pos += (chunk_size - overlap)
    
    for idx, start in enumerate(chunk_starts):
        end = min(start + chunk_size, text_length)
        chunk_text = text[start:end].strip()
        
        if not chunk_text:
            continue
        
        chunk = {
            "id": generate_chunk_id(
                chunk_text,
                {"type": "document", "path": path},
                {"chunk_index": idx, "start_offset": start}
            ),
            "content": chunk_text,
            "source": {
                "type": "document",
                "path": path
            },
            "metadata": {
                "chunk_index": idx,
                "start_offset": start,
                "end_offset": end,
                "language": language,
                "doc_type": ext.lstrip('.'),
                "created_at": datetime.now().isoformat()
            }
        }
        
        if user_id:
            chunk["user_id"] = user_id
        if workspace_id:
            chunk["workspace_id"] = workspace_id
        
        rows.append(chunk)
    
    # Store to database
    if not context:
        context = await vector_store.ensure_default_context()
    
    result = await store_chunks_to_db(rows, vector_store, context)
    result["path"] = path
    result["type"] = "document"
    
    return result


async def ingest_youtube_db(
    url: str,
    vector_store,
    language: str = "en",
    user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    context: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Ingest YouTube video transcript directly to database.
    
    Args:
        url: YouTube video URL
        vector_store: VectorStore instance for database access
        language: Language code
        user_id: Optional user ID
        workspace_id: Optional workspace ID
        context: Optional database context
        
    Returns:
        Dictionary with ingestion results
    """
    vid = _extract_video_id(url)
    if not vid:
        raise ValueError("Could not extract video id from URL")
    
    items = fetch_youtube_transcript(vid, lang=language)
    if not items:
        raise RuntimeError("No official/community transcript. Provide .srt/.vtt/.txt and use ingest-transcript.")
    
    # Convert to timecoded parts
    parts = [(it.get("start", 0.0), it.get("start", 0.0) + it.get("duration", 0.0), it.get("text", ""))
             for it in items]
    
    # Create chunks
    chunks = chunk_timecoded(parts, 1200, 150)
    rows = []
    total = len(chunks)
    
    for idx, (start, end, text) in enumerate(chunks):
        chunk = {
            "id": generate_chunk_id(
                text,
                {"type": "youtube", "url": url},
                {"chunk_index": idx, "start_sec": start}
            ),
            "content": text,
            "source": {
                "type": "youtube",
                "url": url
            },
            "metadata": {
                "chunk_index": idx,
                "start_sec": start,
                "end_sec": end,
                "language": language,
                "video_id": vid,
                "total_chunks": total,
                "created_at": datetime.now().isoformat()
            }
        }
        
        if user_id:
            chunk["user_id"] = user_id
        if workspace_id:
            chunk["workspace_id"] = workspace_id
        
        rows.append(chunk)
    
    # Store to database
    if not context:
        context = await vector_store.ensure_default_context()
    
    result = await store_chunks_to_db(rows, vector_store, context)
    result["video_id"] = vid
    result["url"] = url
    result["type"] = "youtube"
    
    return result


async def migrate_jsonl_to_db(
    jsonl_path: str,
    vector_store,
    context: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Migrate existing JSONL chunks to database.
    
    Args:
        jsonl_path: Path to JSONL file
        vector_store: VectorStore instance
        context: Optional database context
        
    Returns:
        Dictionary with migration results
    """
    if not os.path.exists(jsonl_path):
        return {"migrated": 0, "error": f"File not found: {jsonl_path}"}
    
    chunks = []
    errors = []
    
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    chunks.append(chunk)
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_num}: {e}")
    except Exception as e:
        return {"migrated": 0, "error": f"Failed to read file: {e}"}
    
    if not chunks:
        return {"migrated": 0, "errors": errors}
    
    # Store to database
    if not context:
        context = await vector_store.ensure_default_context()
    
    result = await store_chunks_to_db(chunks, vector_store, context)
    result["source_file"] = jsonl_path
    result["read_errors"] = errors
    
    return result



