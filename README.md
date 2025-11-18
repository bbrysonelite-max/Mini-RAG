# Mini-RAG: Document Retrieval and Question Answering System

[Social media links placeholder]

A lightweight RAG (Retrieval-Augmented Generation) system for ingesting, searching, and querying documents, YouTube transcripts, and other text sources.

## Features

- **Document Ingestion**: Support for PDF, DOCX, Markdown, TXT files
- **YouTube Integration**: Automatic transcript extraction and ingestion
- **Transcript Support**: VTT, SRT, and TXT transcript files
- **Web UI**: Browser-based interface for document management and querying
- **Document Browser**: View, search, and manage ingested documents
- **BM25 Search**: Fast keyword-based retrieval
- **Answer Scoring**: Coverage, groundedness, citation, and brevity metrics

## Quick Start

### Installation

```bash
# Install dependencies
pip install fastapi uvicorn rank-bm25 pypdf docx2txt youtube-transcript-api webvtt srt

# Or use requirements.txt (if available)
pip install -r requirements.txt
```

### Running the Server

```bash
python server.py
# Or use uvicorn directly
uvicorn server:app --host 0.0.0.0 --port 8000
```

Then open your browser to `http://localhost:8000/app/`

### Ingesting Documents

#### Via Web UI
1. Go to the "Ingest" tab
2. Upload files or paste YouTube URLs
3. Wait for processing to complete

#### Via Command Line
```bash
# Ingest a document
python raglite.py ingest-docs --path document.pdf

# Ingest a YouTube video
python raglite.py ingest-youtube --url https://youtube.com/watch?v=...

# Ingest a transcript
python raglite.py ingest-transcript --path transcript.vtt
```

## Project Structure

```
mini-rag/
├── server.py                # FastAPI server with web UI
├── raglite.py               # Core RAG functionality
├── retrieval.py             # Search and indexing
├── score.py                 # Answer scoring
├── scripts/
│   └── ingest/              # Ingestion utilities (docs, transcripts, YouTube)
├── docs/
│   ├── guides/              # Setup and how-to guides
│   ├── notes/               # Planning/analysis docs
│   └── phases/              # Phase completion reports
├── examples/
│   └── transcripts/         # Sample transcript files and source lists
└── out/
    └── chunks.jsonl         # Stored document chunks
```

## API Endpoints

- `POST /ask` - Query the RAG system
- `GET /api/sources` - List all ingested sources
- `GET /api/sources/{id}/chunks` - Get chunks for a source
- `DELETE /api/sources/{id}` - Delete a source
- `POST /api/ingest_files` - Upload and ingest files
- `POST /api/ingest_urls` - Ingest YouTube URLs
- `GET /api/stats` - Get system statistics

## Configuration

Set environment variables:
- `CHUNKS_PATH`: Path to chunks file (default: `out/chunks.jsonl`)

## Security Notes

⚠️ **This is a development/prototype system. For production use, see:**
- `docs/notes/COMMERCIAL_VIABILITY_ANALYSIS.md` - Security and commercial readiness analysis
- `docs/guides/CRITICAL_FIXES_GUIDE.md` - Code-level security fixes

## Documentation

- `docs/notes/COMMERCIAL_VIABILITY_ANALYSIS.md` - Full analysis of commercial readiness
- `docs/guides/CRITICAL_FIXES_GUIDE.md` - Implementation guide for critical fixes
- `docs/guides/QUICK_REFERENCE.md` - Quick checklist and reference

## License

[Add your license here]

## Contributing

[Add contribution guidelines if needed]

