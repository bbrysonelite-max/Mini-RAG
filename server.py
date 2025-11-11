
import os, json, subprocess
from typing import List
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from retrieval import load_chunks, SimpleIndex, format_citation, get_unique_sources, get_chunks_by_source, delete_source_chunks
from score import score_answer
from ingest_youtube import ingest_youtube
from ingest_transcript import ingest_transcript
from ingest_docs import ingest_docs

CHUNKS_PATH = os.environ.get("CHUNKS_PATH", "out/chunks.jsonl")
app = FastAPI(title="RAG Talking Agent (with Ingest)")
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

INDEX=None; CHUNKS=[]
def _count_lines(path):
    try:
        with open(path,"r",encoding="utf-8") as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0

def ensure_index():
    global INDEX, CHUNKS
    if INDEX is None:
        if not os.path.exists(CHUNKS_PATH): raise RuntimeError(f"Missing {CHUNKS_PATH}. Ingest first.")
        CHUNKS = load_chunks(CHUNKS_PATH)
        if not CHUNKS: raise RuntimeError("No chunks loaded.")
        INDEX = SimpleIndex(CHUNKS)

@app.get("/")
def root(): return HTMLResponse('<meta http-equiv="refresh" content="0; url=/app/">')

@app.post("/ask")
def ask(query: str = Form(...), k: int = Form(8)):
    ensure_index()
    ranked = INDEX.search(query, k=k)
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
    return {"count": _count_lines(CHUNKS_PATH), "path": CHUNKS_PATH}

@app.post("/api/ingest_urls")
@app.post("/ingest/urls")
def ingest_urls(urls: str = Form(...), language: str = Form("en")):
    urls_list = [u.strip() for u in urls.splitlines() if u.strip()]
    results = []
    total = 0
    for url in urls_list:
        try:
            r = ingest_youtube(url, out_jsonl=CHUNKS_PATH, language=language)
            written = r.get("written", 0)
            if written == 0 and r.get("stderr"):
                results.append({"url": url, "written": 0, "mode": "transcript", "error": r.get("stderr", "Unknown error")})
            else:
                results.append({"url": url, "written": written, "mode": "transcript"})
            total += written
        except Exception as e:
            # fallback: fetch auto-captions via yt-dlp, then ingest .vtt
            vid = ""
            try:
                vid = subprocess.check_output(["yt-dlp","--print","id","--skip-download",url], text=True).strip().splitlines()[0]
            except Exception:
                pass
            vtt = ""
            try:
                subprocess.check_call(["yt-dlp","--skip-download","--write-auto-sub",
                                       "--sub-lang", language, "--sub-format","vtt",
                                       "-o","%(id)s.%(ext)s", url])
                candidates = []
                if vid:
                    candidates += [f"{vid}.{language}.vtt", f"{vid}.en.vtt", f"{vid}.en-US.vtt"]
                candidates += [p for p in os.listdir(".") if p.endswith(".vtt")]
                for c in candidates:
                    if os.path.exists(c):
                        vtt = c; break
            except Exception:
                vtt = ""
            if vtt:
                r = ingest_transcript(vtt, out_jsonl=CHUNKS_PATH, language=language)
                results.append({"url": url, "written": r.get("written",0), "mode": "auto_captions", "file": vtt})
                total += r.get("written",0)
            else:
                error_msg = f"No transcript or auto-captions found. Video may not have subtitles available."
                results.append({"url": url, "error": error_msg, "written": 0})
    return {"results": results, "total_written": total, "count": _count_lines(CHUNKS_PATH)}

@app.post("/api/ingest_files")
@app.post("/ingest/files")
async def ingest_files(files: List[UploadFile] = File(...), language: str = Form("en")):
    os.makedirs("uploads", exist_ok=True)
    results = []
    total = 0
    for f in files:
        name = f.filename
        path = os.path.join("uploads", name)
        with open(path, "wb") as out: out.write(await f.read())
        lower = name.lower()
        try:
            if lower.endswith((".vtt",".srt",".txt")):
                r = ingest_transcript(path, out_jsonl=CHUNKS_PATH, language=language)
            elif lower.endswith((".pdf",".docx",".md",".markdown",".txt")):
                r = ingest_docs(path, out_jsonl=CHUNKS_PATH, language=language)
            else:
                r = {"error":"unsupported file type"}
        except Exception as e:
            r = {"error": str(e)}
        results.append({"file": name, **r})
        total += int(r.get("written",0) or 0)
    return {"results": results, "total_written": total, "count": _count_lines(CHUNKS_PATH)}

@app.post("/api/dedupe")
@app.post("/dedupe")
def dedupe():
    inp = CHUNKS_PATH; tmp = CHUNKS_PATH + ".tmp"
    seen=set(); kept=0; total=0
    try:
        with open(inp,"r",encoding="utf-8") as f, open(tmp,"w",encoding="utf-8") as g:
            for line in f:
                line=line.strip()
                if not line: continue
                total += 1
                try:
                    obj=json.loads(line)
                except Exception:
                    continue
                k = obj.get("id") or json.dumps(obj, sort_keys=True)
                if k in seen: continue
                seen.add(k); kept += 1
                g.write(json.dumps(obj, ensure_ascii=False)+"\\n")
        os.replace(tmp, inp)
    except FileNotFoundError:
        pass
    return {"kept": kept, "total_before": total, "count": _count_lines(CHUNKS_PATH)}

@app.get("/api/sources")
def get_sources():
    """List all unique sources with metadata."""
    ensure_index()
    sources = get_unique_sources(CHUNKS)
    return {"sources": sources, "count": len(sources)}

@app.get("/api/sources/{source_id}/chunks")
def get_source_chunks(source_id: str):
    """Get all chunks for a specific source."""
    ensure_index()
    chunks = get_chunks_by_source(CHUNKS, source_id)
    return {"chunks": chunks, "count": len(chunks)}

@app.delete("/api/sources/{source_id}")
def delete_source(source_id: str):
    """Delete a source and all its chunks."""
    global INDEX, CHUNKS
    result = delete_source_chunks(CHUNKS_PATH, source_id)
    INDEX = None
    CHUNKS = []
    return result

@app.get("/api/sources/{source_id}/preview")
def get_source_preview(source_id: str, limit: int = 3):
    """Get preview of a source (first few chunks)."""
    ensure_index()
    chunks = get_chunks_by_source(CHUNKS, source_id)
    preview = chunks[:limit]
    return {"preview": preview, "total_chunks": len(chunks)}

@app.get("/api/search")
def search_source(query: str, source_id: str = None, k: int = 8):
    """Search within all chunks or a specific source."""
    ensure_index()
    if source_id:
        source_chunks = get_chunks_by_source(CHUNKS, source_id)
        if not source_chunks:
            return {"chunks": [], "scores": []}
        temp_index = SimpleIndex(source_chunks)
        ranked = temp_index.search(query, k=k)
        results = [(source_chunks[i], score) for i, score in ranked]
    else:
        ranked = INDEX.search(query, k=k)
        results = [(CHUNKS[i], score) for i, score in ranked]
    
    chunks_with_scores = []
    for chunk, score in results:
        chunks_with_scores.append({
            "chunk": chunk,
            "score": float(score),
            "citation": format_citation(chunk)
        })
    return {"chunks": chunks_with_scores, "query": query}

@app.post("/api/rebuild")
@app.post("/rebuild")
def rebuild_index():
    """Rebuild the search index."""
    global INDEX, CHUNKS
    INDEX = None
    CHUNKS = []
    ensure_index()
    return {"status": "rebuilt", "count": len(CHUNKS)}
