import argparse, json, os, re, hashlib, datetime, shutil
from functools import lru_cache
from typing import List, Dict, Any, Tuple

from chunk_backup import ChunkBackupError, create_chunk_backup, restore_chunk_backup

# --- Utilities ---
WORD = re.compile(r"[A-Za-z0-9_']+")

def tok(x: str) -> List[str]:
    return [w.lower() for w in WORD.findall(x or "")]

def stable_id(text: str, extra: dict = None) -> str:
    h = hashlib.sha256()
    h.update((text or "").encode("utf-8"))
    if extra:
        h.update(json.dumps(extra, sort_keys=True).encode("utf-8"))
    return h.hexdigest()[:32]


def ensure_dir(p: str):
    if p:
        os.makedirs(p, exist_ok=True)


def write_jsonl(path: str, rows: List[Dict[str, Any]]):
    """
    Append chunk rows transactionally by staging to a temp file and swapping atomically.

    Copy-on-write ensures we either keep the original file or replace it entirely with
    the augmented file (all-or-nothing) while still creating a backup beforehand.
    """
    ensure_dir(os.path.dirname(path))

    if not rows:
        return

    try:
        create_chunk_backup(path)
    except ChunkBackupError as err:
        raise IOError(f"Unable to create backup for {path}: {err}") from err

    staged_path = f"{path}.staged"

    try:
        with open(staged_path, "w", encoding="utf-8") as staged:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as current:
                    shutil.copyfileobj(current, staged)
            for r in rows:
                staged.write(json.dumps(r, ensure_ascii=False) + "\n")
            staged.flush()
            os.fsync(staged.fileno())
        os.replace(staged_path, path)
    except OSError as err:
        try:
            if os.path.exists(staged_path):
                os.remove(staged_path)
        except OSError:
            pass
        raise IOError(f"Failed to stage chunks to {path}: {err}") from err


def perform_restore(chunks_path: str, backup_path: str = None) -> Dict[str, Any]:
    """
    Restore the chunks file from a snapshot and surface detailed errors.

    Returns a dictionary suitable for CLI/json logging.
    """
    try:
        restored_from, pre_backup = restore_chunk_backup(chunks_path, backup_path)
        return {
            "restored_from": restored_from,
            "pre_backup": pre_backup or None,
        }
    except ChunkBackupError as err:
        return {"error": str(err)}

# --- Chunking ---
def chunk_by_chars(text: str, target: int = 1200, overlap: int = 150) -> List[str]:
    if not text:
        return []
    chunks, i, n = [], 0, len(text)
    while i < n:
        end = min(i + target, n)
        chunk = text[i:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        i = max(0, end - overlap)
    return chunks

def chunk_timecoded(parts: List[Tuple[float, float, str]], target: int = 1200, overlap: int = 150):
    chunks, cur, cur_len, cur_start = [], [], 0, None
    for s, e, t in parts:
        if cur_start is None:
            cur_start = s
        if cur_len + len(t) > target and cur:
            text = "\n".join(x[2] for x in cur).strip()
            chunks.append((cur_start, cur[-1][1], text))
            # overlap by characters from the end
            tail, tl = [], 0
            for it in reversed(cur):
                if tl >= overlap:
                    break
                tail.append(it)
                tl += len(it[2])
            cur = list(reversed(tail))
            cur_len = sum(len(x[2]) for x in cur)
            cur_start = cur[0][0] if cur else None
        cur.append((s, e, t))
        cur_len += len(t)
    if cur:
        text = "\n".join(x[2] for x in cur).strip()
        chunks.append((cur_start, cur[-1][1], text))
    return chunks

# --- Transcript ingestion (.srt/.vtt/.txt) ---
def parse_srt(path: str):
    import srt
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()
    subs = list(srt.parse(data))
    parts = []
    for s in subs:
        parts.append((s.start.total_seconds(), s.end.total_seconds(), s.content.replace("\n", " ").strip()))
    return parts

def parse_vtt(path: str):
    import webvtt
    parts = []
    for c in webvtt.read(path):
        h, m, s = c.start.split(":")
        start = int(h) * 3600 + int(m) * 60 + float(s)
        h, m, s = c.end.split(":")
        end = int(h) * 3600 + int(m) * 60 + float(s)
        parts.append((start, end, c.text.replace("\n", " ").strip()))
    return parts

def ingest_transcript(path: str, out_jsonl="out/chunks.jsonl", language="en", user_id=None, workspace_id=None):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".srt":
        parts = parse_srt(path)
    elif ext == ".vtt":
        parts = parse_vtt(path)
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read().strip()
        parts = [(0.0, 0.0, txt)]
    chunks = chunk_timecoded(parts, 1200, 150)
    rows, total = [], len(chunks)
    for idx, (start, end, text) in enumerate(chunks):
        rid = stable_id(text, {"path": path, "start": start, "end": end})
        chunk = {
            "id": rid,
            "source": {"type": "transcript_file", "path": path},
            "content": text,
            "metadata": {
                "language": language, "chunk_index": idx, "chunk_count": total,
                "start_sec": float(round(start, 2)), "end_sec": float(round(end, 2)),
                "created_at": datetime.datetime.utcnow().isoformat() + "Z"
            }
        }
        # Add user_id if provided
        if user_id:
            chunk["user_id"] = user_id
        if workspace_id:
            chunk["workspace_id"] = workspace_id
        rows.append(chunk)
    write_jsonl(out_jsonl, rows)
    return {"written": len(rows), "path": out_jsonl}

# --- Document ingestion (pdf/docx/md/txt) ---
def read_pdf(path: str) -> str:
    from pypdf import PdfReader
    texts = []
    reader = PdfReader(path)
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except (ValueError, AttributeError, KeyError):
            continue
    return "\n".join(texts)

def read_docx(path: str) -> str:
    import docx2txt
    return docx2txt.process(path) or ""

@lru_cache(maxsize=128)
def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def ingest_docs(path: str, out_jsonl="out/chunks.jsonl", language="en", user_id=None, workspace_id=None):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text = read_pdf(path)
    elif ext == ".docx":
        text = read_docx(path)
    else:
        text = read_text(path)
    chunks = chunk_by_chars(text, 1200, 150)
    rows, total = [], len(chunks)
    for idx, c in enumerate(chunks):
        rid = stable_id(c, {"path": path, "idx": idx})
        chunk = {
            "id": rid,
            "source": {"type": "document", "path": path},
            "content": c,
            "metadata": {
                "language": language, "chunk_index": idx, "chunk_count": total,
                "doc_section": None, "created_at": datetime.datetime.utcnow().isoformat() + "Z"
            }
        }
        # Add user_id if provided
        if user_id:
            chunk["user_id"] = user_id
        if workspace_id:
            chunk["workspace_id"] = workspace_id
        rows.append(chunk)
    write_jsonl(out_jsonl, rows)
    return {"written": len(rows), "path": out_jsonl}

# --- YouTube ingestion (transcripts only; TOS friendly) ---
def _extract_video_id(url: str):
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else None

@lru_cache(maxsize=128)
def fetch_youtube_transcript(video_id: str, lang="en"):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            t = transcripts.find_transcript([lang])
            return t.fetch()
        except (NoTranscriptFound, TranscriptsDisabled):
            pass
        for t in transcripts:
            try:
                return t.fetch()
            except (NoTranscriptFound, TranscriptsDisabled):
                continue
    except (TranscriptsDisabled, NoTranscriptFound, ValueError):
        return None
    return None

def ingest_youtube(url: str, out_jsonl="out/chunks.jsonl", language="en", user_id=None, workspace_id=None):
    vid = _extract_video_id(url)
    if not vid:
        raise ValueError("Could not extract video id from URL")
    items = fetch_youtube_transcript(vid, lang=language)
    if not items:
        raise RuntimeError("No official/community transcript. Provide .srt/.vtt/.txt and use ingest-transcript.")
    parts = [(it.get("start", 0.0), it.get("start", 0.0) + it.get("duration", 0.0), it.get("text", "")) for it in items]
    chunks = chunk_timecoded(parts, 1200, 150)
    rows, total = [], len(chunks)
    for idx, (start, end, text) in enumerate(chunks):
        rid = stable_id(text, {"url": url, "start": start, "end": end})
        chunk = {
            "id": rid,
            "source": {"type": "youtube", "url": url},
            "content": text,
            "metadata": {
                "language": language, "chunk_index": idx, "chunk_count": total,
                "start_sec": float(round(start, 2)), "end_sec": float(round(end, 2)),
                "created_at": datetime.datetime.utcnow().isoformat() + "Z"
            }
        }
        # Add user_id if provided
        if user_id:
            chunk["user_id"] = user_id
        if workspace_id:
            chunk["workspace_id"] = workspace_id
        rows.append(chunk)
    write_jsonl(out_jsonl, rows)
    return {"written": len(rows), "path": out_jsonl, "video_id": vid}

# --- Retrieval + scoring ---
from rank_bm25 import BM25Okapi

def load_chunks(path: str):
    items = []
    if not os.path.exists(path):
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return items

class SimpleIndex:
    def __init__(self, chunks: List[Dict[str, Any]]):
        self.chunks = chunks
        self.docs = [c.get("content", "") for c in chunks]
        self.tokens = [tok(d) for d in self.docs]
        self.bm25 = BM25Okapi(self.tokens)
    def search(self, query: str, k: int = 8):
        q = tok(query or "")
        scores = self.bm25.get_scores(q)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:k]

def citation(c: Dict[str, Any]) -> str:
    src, meta = c.get("source", {}), c.get("metadata", {})
    if src.get("type") == "youtube":
        url, start = src.get("url") or "", meta.get("start_sec")
        return f"{url}?t={int(start)}" if start is not None else url
    if src.get("type") == "document":
        path, sec = src.get("path") or "", meta.get("doc_section")
        return f"{path}#{sec}" if sec else path
    return src.get("path") or src.get("url") or ""

def ngram_overlap(a: str, b: str, n: int = 3) -> float:
    def grams(x):
        toks = tok(x)
        return set(tuple(toks[i:i+n]) for i in range(max(0, len(toks)-n+1)))
    A, B = grams(a), grams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A)

def score_answer(question: str, answer: str, contexts: List[Dict[str, Any]]):
    ctx = " ".join([c.get("content", "") for c in contexts])
    cov = ngram_overlap(answer, ctx, 3)
    sents = re.split(r"(?<=[.!?])\s+", answer.strip()) if answer.strip() else []
    if not sents:
        sents = [answer]
    grounded = sum(ngram_overlap(s, ctx, 3) for s in sents) / max(1, len(sents))
    cited = 1.0 if "http" in (answer or "") else 0.0
    brevity = min(1.0, max(0.0, len(answer) / 120))
    total = (0.35*cov + 0.35*grounded + 0.2*cited + 0.1*brevity) * 100
    return {
        "coverage": round(cov*100, 1),
        "groundedness": round(grounded*100, 1),
        "citations": round(cited*100, 1),
        "brevity": round(brevity*100, 1),
        "total": round(total, 1)
    }

# --- FastAPI server + UI ---
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
app = FastAPI(title="RAG Talking Agent (Lite)")

CHUNKS_PATH = "out/chunks.jsonl"
INDEX = None
CHUNKS = []

def ensure_index():
    global INDEX, CHUNKS
    if INDEX is None:
        CHUNKS = load_chunks(CHUNKS_PATH)
        if not CHUNKS:
            raise RuntimeError(f"No chunks at {CHUNKS_PATH}. Ingest first.")
        INDEX = SimpleIndex(CHUNKS)

HTML_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>RAG Talking Agent</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}
header{display:flex;gap:.6rem;align-items:center}
textarea{width:100%;min-height:90px;padding:.6rem;border:1px solid #ddd;border-radius:8px}
.btn{padding:.6rem 1rem;border-radius:8px;border:1px solid #333;background:#111;color:#fff;cursor:pointer}
.badge{background:#eee;border-radius:6px;padding:.2rem .5rem;margin-right:.25rem}
.small{color:#555;font-size:.9rem}
pre{background:#f7f7f7;padding:1rem;border-radius:8px;overflow:auto}
.mic{padding:.4rem .8rem;border:1px solid #ccc;border-radius:8px;cursor:pointer}
.mic.listening{background:#fee;border-color:#f66}
</style></head>
<body>
<header><h2>RAG Talking Agent</h2><span class="small">Ask with voice or text. Results include citations and a score.</span></header>
<div>
  <button id="mic" class="mic">🎤 Start listening</button>
  <div class="small">Uses the Web Speech API (Chrome/Edge).</div>
  <textarea id="q" placeholder="Ask about your ingested videos or guides..."></textarea>
  <button id="ask" class="btn">Ask</button>
</div>
<h3>Answer</h3>
<pre id="ans"></pre>
<div id="score"></div>
<button id="speak" class="btn">🔊 Read aloud</button>
<script>
const q = document.getElementById('q');
const ans = document.getElementById('ans');
const scoreDiv = document.getElementById('score');
const micBtn = document.getElementById('mic');
const askBtn = document.getElementById('ask');
const speakBtn = document.getElementById('speak');

let rec=null,listening=false;
function toggleMic(){
  if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)){
    alert('Web Speech API not available in this browser. Type instead.'); return;
  }
  if(!rec){
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    rec = new SR(); rec.lang='en-US'; rec.interimResults=true; rec.continuous=true;
    rec.onresult = (e)=>{ let txt=''; for(let i=0;i<e.results.length;i++){ txt += e.results[i][0].transcript + ' '; } q.value = txt.trim(); };
    rec.onend = ()=>{ listening=false; micBtn.classList.remove('listening'); micBtn.textContent='🎤 Start listening'; };
  }
  if(!listening){ rec.start(); listening=true; micBtn.classList.add('listening'); micBtn.textContent='🛑 Stop listening'; }
  else { rec.stop(); }
}
micBtn.addEventListener('click', toggleMic);

async function ask(){
  const form = new FormData(); form.append('query', q.value || ''); form.append('k', '8');
  const r = await fetch('/ask', { method:'POST', body: form });
  const data = await r.json();
  ans.textContent = data.answer || '';
  const s = data.score || {};
  scoreDiv.innerHTML = ['coverage','groundedness','citations','brevity','total'].map(k => (
    `<span class="badge">${k}: ${s[k] ?? '-'}</span>`
  )).join('');
}
askBtn.addEventListener('click', ask);

function speak(){
  if(!('speechSynthesis' in window)){ alert('speechSynthesis not available'); return; }
  const u = new SpeechSynthesisUtterance(ans.textContent); window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);
}
speakBtn.addEventListener('click', speak);
</script>
</body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_PAGE

@app.post("/ask")
def ask(query: str = Form(...), k: int = Form(8)):
    ensure_index()
    ranked = INDEX.search(query, k=k)
    top = [CHUNKS[i] for i, _ in ranked]
    snippets = [c.get("content", "").strip() for c in top[:3]]
    cites = [citation(c) for c in top[:3]]
    text = " ".join(snippets)
    if len(text) > 900:
        text = text[:900].rsplit(" ", 1)[0] + "…"
    answer = f"{text}\n\nSources:\n" + "\n".join(f"- {u}" for u in cites)
    sc = score_answer(query, answer, top)
    return {"answer": answer, "citations": cites, "score": sc}

# --- CLI ---
def run_server(chunks: str, host: str, port: int):
    global CHUNKS_PATH, INDEX
    CHUNKS_PATH = chunks
    INDEX = None
    import uvicorn
    uvicorn.run(app, host=host, port=port)

def main():
    p = argparse.ArgumentParser(prog="raglite")
    sub = p.add_subparsers(dest="cmd", required=True)

    y = sub.add_parser("ingest-youtube"); y.add_argument("--url", required=True); y.add_argument("--out", default="out/chunks.jsonl"); y.add_argument("--language", default="en"); y.add_argument("--user-id", default=None); y.add_argument("--workspace-id", default=None)
    t = sub.add_parser("ingest-transcript"); t.add_argument("--path", required=True); t.add_argument("--out", default="out/chunks.jsonl"); t.add_argument("--language", default="en"); t.add_argument("--user-id", default=None); t.add_argument("--workspace-id", default=None)
    d = sub.add_parser("ingest-docs"); d.add_argument("--path", required=True); d.add_argument("--out", default="out/chunks.jsonl"); d.add_argument("--language", default="en"); d.add_argument("--user-id", default=None); d.add_argument("--workspace-id", default=None)

    s = sub.add_parser("serve"); s.add_argument("--chunks", default="out/chunks.jsonl"); s.add_argument("--host", default="127.0.0.1"); s.add_argument("--port", type=int, default=8000)
    r = sub.add_parser("restore-backup"); r.add_argument("--chunks", default="out/chunks.jsonl"); r.add_argument("--backup", default=None)

    args = p.parse_args()
    if args.cmd == "ingest-youtube":
        res = ingest_youtube(args.url, out_jsonl=args.out, language=args.language, user_id=args.user_id, workspace_id=args.workspace_id)
    elif args.cmd == "ingest-transcript":
        res = ingest_transcript(args.path, out_jsonl=args.out, language=args.language, user_id=args.user_id, workspace_id=args.workspace_id)
    elif args.cmd == "ingest-docs":
        res = ingest_docs(args.path, out_jsonl=args.out, language=args.language, user_id=args.user_id, workspace_id=args.workspace_id)
    elif args.cmd == "serve":
        run_server(args.chunks, args.host, args.port); return
    elif args.cmd == "restore-backup":
        res = perform_restore(args.chunks, args.backup)
    else:
        res = {"error": "unknown command"}
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
