# Mini-RAG: Production-Ready RAG System

> **🎉 PROJECT COMPLETE - Ready to Deploy!**  
> **👉 See [START_HERE.md](START_HERE.md) for one-command deployment**

A production-ready, multi-tenant RAG (Retrieval-Augmented Generation) system with enterprise features: OAuth authentication, Stripe billing, Redis caching, comprehensive monitoring, and full deployment automation.

## Features

- **Multi-Tenant Architecture**: Organization & workspace isolation with role-based access
- **Authentication**: Google OAuth + JWT sessions + API keys with scope enforcement
- **Document Ingestion**: Support for PDF, DOCX, Markdown, TXT files
- **YouTube Integration**: Automatic transcript extraction and ingestion
- **Transcript Support**: VTT, SRT, and TXT transcript files
- **Hybrid Search**: BM25 + pgvector embeddings (OpenAI/Anthropic)
- **Web UI**: Browser-based interface with workspace switching
- **Document Browser**: View, search, and manage ingested documents
- **Usage Quotas**: Per-workspace request & storage limits
- **Billing Integration**: Stripe subscriptions with automated trial management
- **Observability**: Prometheus metrics + OpenTelemetry traces + structured logging
- **Answer Scoring**: Coverage, groundedness, citation, and brevity metrics

## 🚀 Quick Start

### One-Command Deploy

```bash
# Local (Docker Compose)
./scripts/one_click_deploy.sh local

# Production - Choose your platform
./scripts/one_click_deploy.sh heroku   # Easiest
./scripts/one_click_deploy.sh fly      # Fastest
./scripts/one_click_deploy.sh render   # Best for teams
```

### Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp PRODUCTION_ENV_TEMPLATE .env
# Edit .env with your credentials

# 3. Start services
docker-compose up -d

# 4. Initialize database
docker exec -i mini-rag-db psql -U postgres -d rag_brain < db_schema.sql

# 5. Verify health
curl http://localhost:8000/health
```

Then open your browser to `http://localhost:8000/app/`

### Running with Docker

```bash
# Full stack with Redis + PostgreSQL
docker-compose up --build

# Wait for health checks
curl http://localhost:8000/health
```

This starts PostgreSQL + Redis + FastAPI app. Browse to `http://localhost:8000/app` when healthy.

### Production Deployment

See `LAUNCH_CHECKLIST.md` for step-by-step guide or use:
```bash
./scripts/one_click_deploy.sh [heroku|fly|render]
```

Full deployment takes ~15 minutes including database setup.

### React Development Server

A new Vite/React shell lives in `frontend-react/`. To run it:

```bash
cd frontend-react
npm install
npm run dev
```

The dev server proxy points to `http://localhost:8000` for API calls. Production builds are created via `npm run build`.

After building, the FastAPI app will serve the React UI at `http://localhost:8000/app-react` (the legacy UI remains at `/app` until the migration is complete).

### Optional: OpenTelemetry / Logging

Set the following environment variables to enable tracing + structured log enrichment:

```
OTEL_ENABLED=true
OTEL_SERVICE_NAME=mini-rag
# optional:
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel-collector.example.com/v1/traces
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer xyz
```

When enabled, the server emits correlation IDs (`X-Request-ID`) and OpenTelemetry traces that you can ingest into your preferred backend.

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

## Security & Production Readiness

✅ **Authentication & authorization required** for all data operations (OAuth + API keys)  
✅ **Multi-tenant isolation** via workspace-scoped queries and storage  
✅ **Billing enforcement** blocks ingestion when trials expire or subscriptions lapse  
✅ **Production checklist** available in `docs/guides/QUICK_REFERENCE.md`

⚠️ **Before deploying:**
1. Replace placeholder secrets in `.env` (see `env.template`)
2. Purge demo data from `out/chunks.jsonl`
3. Configure real Stripe keys + webhook endpoint
4. Set up PostgreSQL with pgvector extension
5. Review `docker-compose.yml` secret validation

For detailed security analysis:
- `docs/guides/QUICK_REFERENCE.md` - Production checklist
- `docs/guides/BILLING_AND_API.md` - Stripe setup & API usage

## Documentation

- `docs/notes/COMMERCIAL_VIABILITY_ANALYSIS.md` - Full analysis of commercial readiness
- `docs/guides/CRITICAL_FIXES_GUIDE.md` - Implementation guide for critical fixes
- `docs/guides/QUICK_REFERENCE.md` - Quick checklist and reference
- `docs/guides/BILLING_AND_API.md` - Stripe setup, billing endpoints, and Postman/SDK onboarding
- `docs/infra/CI_SETUP.md` - CI/CD workflow overview and required secrets
- `docs/guides/REACT_MIGRATION.md` - Plan for rolling out the new React shell alongside the legacy UI

## Python SDK & Postman Collection

- **SDK:** `clients/sdk.py` ships a minimal `MiniRAGClient` that wraps `/api/v1/ask`, ingest endpoints, and billing helpers. Install `httpx`, copy the file into your project, and initialize it with `base_url` + API key.
- **Postman:** Import `docs/postman/mini-rag.postman_collection.json` to exercise ask, ingest, and billing flows with environment variables (`{{base_url}}`, `{{api_key}}`, etc.).

## License

[Add your license here]

## Contributing

[Add contribution guidelines if needed]

