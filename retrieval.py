
import json, os, re, hashlib
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

from chunk_backup import ChunkBackupError, create_chunk_backup
_WORD = re.compile(r"[A-Za-z0-9_]+")
def _tok(x): return [w.lower() for w in _WORD.findall(x or "")]
def load_chunks(path):
    items=[]
    with open(path,"r",encoding="utf-8") as f:
        for ln in f:
            ln=ln.strip()
            if not ln: continue
            try: items.append(json.loads(ln))
            except json.JSONDecodeError: pass
    return items
class SimpleIndex:
    def __init__(self,chunks):
        self.chunks=chunks
        docs=[c.get("content","") for c in chunks]
        toks=[_tok(d) for d in docs]
        self.bm25=BM25Okapi(toks)
    def search(self,query,k=8,user_id=None,workspace_id=None):
        q=_tok(query or "")
        scores=self.bm25.get_scores(q)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        
        if not user_id and not workspace_id:
            return ranked[:k]

        filtered = []
        for idx, score in ranked:
            chunk = self.chunks[idx]

            if workspace_id:
                chunk_workspace = chunk.get("workspace_id")
                # Allow legacy chunks that don't specify workspace
                if chunk_workspace is not None and chunk_workspace != workspace_id:
                    continue

            if user_id:
                chunk_user_id = chunk.get("user_id")
                if chunk_user_id is not None and chunk_user_id != user_id:
                    continue

            filtered.append((idx, score))
            if len(filtered) >= k:
                break
        return filtered
def format_citation(chunk):
    src=chunk.get("source",{}); meta=chunk.get("metadata",{})
    if src.get("type")=="youtube":
        url=src.get("url") or ""; s=meta.get("start_sec")
        return f"{url}?t={int(s)}" if s is not None else url
    path=src.get("path") or src.get("url") or ""
    sec=meta.get("doc_section")
    return f"{path}#{sec}" if sec else path

def _source_id(source: Dict[str, Any]) -> str:
    """Generate stable ID for a source."""
    h = hashlib.sha256()
    src_type = source.get("type", "")
    path_or_url = source.get("path") or source.get("url") or ""
    h.update(f"{src_type}:{path_or_url}".encode("utf-8"))
    return h.hexdigest()[:32]

def get_unique_sources(chunks: List[Dict[str, Any]], user_id: str = None, workspace_id: str = None) -> List[Dict[str, Any]]:
    """Extract unique sources with metadata from chunks, optionally filtered by user_id."""
    sources_map = {}
    for chunk in chunks:
        # Filter by user_id if provided
        if user_id:
            chunk_user_id = chunk.get("user_id")
            # Only include if chunk belongs to user or has no user_id (legacy/public)
            if chunk_user_id is not None and chunk_user_id != user_id:
                continue
        if workspace_id:
            chunk_workspace_id = chunk.get("workspace_id")
            if chunk_workspace_id is not None and chunk_workspace_id != workspace_id:
                continue
        
        src = chunk.get("source", {})
        if not src:
            continue
        sid = _source_id(src)
        if sid not in sources_map:
            meta = chunk.get("metadata", {})
            sources_map[sid] = {
                "id": sid,
                "type": src.get("type", "unknown"),
                "path": src.get("path", ""),
                "url": src.get("url", ""),
                "chunk_count": 0,
                "first_seen": meta.get("created_at", ""),
                "language": meta.get("language", "en"),
                "display_name": src.get("url") or src.get("path", "Unknown")
            }
        sources_map[sid]["chunk_count"] += 1
    return list(sources_map.values())

def get_chunks_by_source(chunks: List[Dict[str, Any]], source_id: str, user_id: str = None, workspace_id: str = None) -> List[Dict[str, Any]]:
    """Get all chunks for a specific source, optionally filtered by user_id."""
    result = []
    for c in chunks:
        if _source_id(c.get("source", {})) == source_id:
            # Filter by user_id if provided
            if user_id:
                chunk_user_id = c.get("user_id")
                # Only include if chunk belongs to user or has no user_id
                if chunk_user_id is not None and chunk_user_id != user_id:
                    continue
            if workspace_id:
                chunk_workspace_id = c.get("workspace_id")
                if chunk_workspace_id is not None and chunk_workspace_id != workspace_id:
                    continue
            result.append(c)
    return result

def delete_source_chunks(path: str, source_id: str, workspace_id: str = None) -> Dict[str, Any]:
    """Delete all chunks for a source from the chunks file."""
    chunks = load_chunks(path)
    to_keep = []
    deleted_count = 0
    for chunk in chunks:
        if _source_id(chunk.get("source", {})) != source_id:
            to_keep.append(chunk)
            continue

        if workspace_id:
            chunk_workspace_id = chunk.get("workspace_id")
            if chunk_workspace_id is not None and chunk_workspace_id != workspace_id:
                to_keep.append(chunk)
                continue

        deleted_count += 1
        continue

    if deleted_count == 0:
        return {"deleted": 0, "kept": len(to_keep), "backup_path": None}

    # Snapshot current state before rewriting so accidental data loss is recoverable.
    try:
        backup_path = create_chunk_backup(path)
    except ChunkBackupError as err:
        raise IOError(f"Unable to create backup for {path}: {err}") from err
    
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            for chunk in to_keep:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        os.replace(tmp_path, path)
    except OSError as err:
        # Clean up any partially written temp file to avoid confusion.
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise IOError(f"Failed to rewrite chunks file {path}: {err}") from err

    return {"deleted": deleted_count, "kept": len(to_keep), "backup_path": backup_path}
