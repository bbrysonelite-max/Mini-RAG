"""
Database-backed chunk storage and retrieval.

This module provides functions to store and retrieve chunks directly from PostgreSQL,
eliminating the dependency on JSONL file storage.
"""

import json
import uuid
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_chunk_id(content: str, source: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    """Generate a stable UUID for a chunk based on its content and metadata."""
    h = hashlib.sha256()
    h.update(content.encode('utf-8'))
    h.update(json.dumps(source, sort_keys=True).encode('utf-8'))
    h.update(str(metadata.get('chunk_index', 0)).encode('utf-8'))
    return str(uuid.uuid5(uuid.NAMESPACE_URL, h.hexdigest()))


async def store_chunks_to_db(
    chunks: List[Dict[str, Any]],
    vector_store,
    context: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Store chunks directly to PostgreSQL database.
    
    Args:
        chunks: List of chunk dictionaries with content, source, metadata
        vector_store: VectorStore instance
        context: Optional context with organization/workspace/project IDs
        
    Returns:
        Dictionary with results (written count, errors, etc.)
    """
    if not chunks:
        return {"written": 0, "errors": 0}
    
    if not context:
        context = await vector_store.ensure_default_context()
    
    # Prepare chunks for insertion
    chunk_entries = []
    for chunk in chunks:
        chunk_id = chunk.get("id")
        if not chunk_id:
            # Generate stable ID if not provided
            chunk_id = generate_chunk_id(
                chunk.get("content", ""),
                chunk.get("source", {}),
                chunk.get("metadata", {})
            )
        
        chunk_entries.append((chunk_id, chunk))
    
    # Store to database
    try:
        await vector_store.ensure_chunks(chunk_entries, context)
        logger.info(f"Stored {len(chunks)} chunks to database")
        return {
            "written": len(chunks),
            "errors": 0,
            "storage": "database"
        }
    except Exception as e:
        logger.error(f"Failed to store chunks to database: {e}")
        return {
            "written": 0,
            "errors": len(chunks),
            "error": str(e),
            "storage": "database"
        }


async def load_chunks_from_db(vector_store) -> List[Dict[str, Any]]:
    """
    Load all chunks from PostgreSQL database.
    
    Args:
        vector_store: VectorStore instance
        
    Returns:
        List of chunk dictionaries
    """
    try:
        chunks = await vector_store.fetch_all_chunks()
        logger.info(f"Loaded {len(chunks)} chunks from database")
        return chunks
    except Exception as e:
        logger.error(f"Failed to load chunks from database: {e}")
        return []


async def delete_chunks_by_source_db(
    source_id: str,
    vector_store,
    workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Delete chunks by source ID from database.
    
    Args:
        source_id: Source identifier
        vector_store: VectorStore instance
        workspace_id: Optional workspace filter
        
    Returns:
        Dictionary with deletion results
    """
    try:
        # Get database connection
        db = vector_store.db
        
        # Build query
        query = """
            DELETE FROM chunks 
            WHERE id IN (
                SELECT c.id FROM chunks c
                WHERE c.text LIKE %s
        """
        params = [f"%{source_id}%"]
        
        if workspace_id:
            query += " AND c.workspace_id = %s"
            params.append(workspace_id)
        
        query += ")"
        
        # Execute deletion
        await db.execute(query, tuple(params))
        
        logger.info(f"Deleted chunks for source {source_id}")
        return {"deleted": True, "source_id": source_id}
    except Exception as e:
        logger.error(f"Failed to delete chunks for source {source_id}: {e}")
        return {"deleted": False, "source_id": source_id, "error": str(e)}


async def search_chunks_db(
    query: str,
    vector_store,
    k: int = 8,
    workspace_id: Optional[str] = None,
    use_vector: bool = False
) -> List[Tuple[int, float, Dict[str, Any]]]:
    """
    Search chunks in database using full-text or vector search.
    
    Args:
        query: Search query
        vector_store: VectorStore instance
        k: Number of results
        workspace_id: Optional workspace filter
        use_vector: Whether to use vector search (requires embeddings)
        
    Returns:
        List of (index, score, chunk) tuples
    """
    try:
        db = vector_store.db
        
        if use_vector:
            # Vector search (requires embeddings to be generated)
            # This is a placeholder - actual implementation would need query embedding
            logger.warning("Vector search not yet implemented, falling back to text search")
        
        # Full-text search using PostgreSQL
        search_query = """
            SELECT 
                id,
                text as content,
                position,
                ts_rank(to_tsvector('english', text), plainto_tsquery('english', %s)) as score
            FROM chunks
            WHERE to_tsvector('english', text) @@ plainto_tsquery('english', %s)
        """
        params = [query, query]
        
        if workspace_id:
            search_query += " AND workspace_id = %s"
            params.append(workspace_id)
        
        search_query += " ORDER BY score DESC LIMIT %s"
        params.append(k)
        
        results = await db.fetch_all(search_query, tuple(params))
        
        # Format results
        formatted_results = []
        for idx, row in enumerate(results):
            chunk = {
                "id": str(row["id"]),
                "content": row["content"],
                "metadata": {"chunk_index": row.get("position", idx)},
                "source": {"type": "database"}
            }
            formatted_results.append((idx, float(row["score"]), chunk))
        
        return formatted_results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


async def export_chunks_to_jsonl(
    vector_store,
    output_path: str = "out/chunks_export.jsonl",
    workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Export chunks from database to JSONL file (for backup/migration).
    
    Args:
        vector_store: VectorStore instance
        output_path: Output file path
        workspace_id: Optional workspace filter
        
    Returns:
        Dictionary with export results
    """
    import os
    from pathlib import Path
    
    try:
        # Create output directory if needed
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Load chunks from database
        chunks = await load_chunks_from_db(vector_store)
        
        # Filter by workspace if specified
        if workspace_id:
            chunks = [c for c in chunks if c.get("workspace_id") == workspace_id]
        
        # Write to JSONL
        with open(output_path, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        
        logger.info(f"Exported {len(chunks)} chunks to {output_path}")
        return {
            "exported": len(chunks),
            "path": output_path
        }
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return {
            "exported": 0,
            "error": str(e)
        }

