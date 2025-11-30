# Mini-RAG: Production-Ready _(When Configured)_ RAG System

> **⚠️ Reality Check:** The codebase implements enterprise features, but the shared Railway deployment still runs with `LOCAL_MODE=true`, BM25-only search, no Redis cache, and Stripe disabled. Read `DEPLOYMENT_STATUS.md` before promising “production ready.”
>
> **👉 See [START_HERE.md](START_HERE.md) for setup steps _after_ you provision real secrets and services.**

Mini-RAG targets a multi-tenant RAG (Retrieval-Augmented Generation) system with OAuth, Stripe, quotas, observability, and deployment automation. Those capabilities only become “production ready” once you replace placeholders, scrub demo data, and enable the optional services described below.

## Features

- **Multi-Tenant Architecture:** Organization & workspace isolation with role-based access (requires PostgreSQL; shipped)
- **Authentication:** Google OAuth + JWT sessions + API keys (code ready, but Railway defaults to `LOCAL_MODE=true`)
- **Document Ingestion:** PDF, DOCX, Markdown, TXT, VTT, SRT, YouTube transcripts (shipping)
- **Hybrid Search:** BM25 always on; pgvector embeddings available _after_ you supply OpenAI/Anthropic keys and run the embedding job
- **Web UI:** Legacy HTML app (`/app`) plus preview React shell (`/app-react`) – both need real auth + billing context to be fully accurate
- **Usage Quotas:** Workspace-level request and chunk limits enforced when DATABASE_URL is configured
- **Billing Integration:** Stripe checkout/portal/webhooks implemented but **inactive** until real `STRIPE_*` secrets exist
- **Caching & Dedup:** Redis-backed cache/deduplicator implemented but **disabled by default**
- **Observability:** Prometheus metrics + OpenTelemetry traces (available; exporters optional)
- **Answer Scoring:** Coverage, groundedness, citation, and brevity metrics in responses

### Current Deployment Reality (Nov 29, 2025)

| Area | Status | Required to flip to “prod-ready” |
|------|--------|-----------------------------------|
| Auth | `LOCAL_MODE=true` (no login required) | Set `LOCAL_MODE=false`, configure Google OAuth, verify cookies |
| Search | BM25 only | Provide OpenAI/Anthropic keys, generate embeddings, enable pgvector |
| Caching/Dedup | Disabled | Provision Redis + set `REDIS_ENABLED=true` |
| Billing | Stripe keys unset | Supply real `STRIPE_*` secrets, verify webhook endpoint |
| Background jobs | Disabled | Set `BACKGROUND_JOBS_ENABLED=true`, monitor queue |
| Data | `out/chunks.jsonl` ships demo rows | Scrub sample data before launch |

See `DEPLOYMENT_STATUS.md` for the authoritative checklist.

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
# Edit .env with **real** credentials (SECRET_KEY, Google OAuth, PostgreSQL, Stripe, OpenAI, Redis)
# Remove demo data from out/chunks.jsonl or point CHUNKS_PATH elsewhere

# 3. Start services
docker-compose up -d

# 4. Initialize database
docker exec -i mini-rag-db psql -U postgres -d rag_brain < db_schema.sql

# 5. Verify health
curl http://localhost:8000/health
# 6. Disable LOCAL_MODE once auth is configured
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

> ⚠️ The React shell is still in preview: it reuses the REST endpoints but lacks full auth/billing context until `LOCAL_MODE=false` and Stripe are active. Keep `/app` as the default UI until React reaches feature parity.

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
1. Replace placeholder secrets in `.env` (SECRET_KEY, Google OAuth, OpenAI, Stripe, Redis)
2. Purge demo data from `out/chunks.jsonl` or point `CHUNKS_PATH` at real tenant data
3. Configure real Stripe keys + webhook endpoint (or disable billing entirely)
4. Set up PostgreSQL with pgvector extension and run `db_schema.sql`
5. Review `docker-compose.yml` / Railway variables so `ALLOW_INSECURE_DEFAULTS=false`
6. Turn off `LOCAL_MODE` once OAuth is verified end-to-end

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

