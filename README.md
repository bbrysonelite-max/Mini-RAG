# Second Brain - Enterprise RAG System

> **Build your personal knowledge base with AI-powered search and command workflows.**

Second Brain is a production-ready RAG (Retrieval-Augmented Generation) system that transforms documents, videos, and text into a searchable, AI-queryable knowledge base.

## ✨ Features

### Core Capabilities
- **Multi-format Ingestion:** PDF, Word, Markdown, Text, Images (OCR), VTT/SRT subtitles, YouTube transcripts
- **AI-Powered Search:** Hybrid BM25 + vector search with pgvector
- **Command Workflows:** Build prompts, workflows, customer avatars, expert instructions, and more
- **Multi-Tenant Architecture:** Organizations, workspaces, and projects with role-based access

### Modern UI/UX (New!)
- **Toast Notifications:** Elegant slide-in feedback for all actions
- **Loading States:** Animated spinners and skeleton loaders
- **Empty States:** Helpful guidance when no data exists
- **Keyboard Shortcuts:** `⌘+K` (search), `⌘+I` (ingest), `⌘+S` (sources), `?` (help)
- **Drag & Drop:** Enhanced file upload with previews and animations
- **Accessibility:** WCAG 2.1 AA compliant with full keyboard navigation

### Enterprise Features
- **Authentication:** Google OAuth + JWT sessions + API keys
- **Billing:** Stripe integration with subscriptions and quotas
- **Database:** PostgreSQL with pgvector for persistent, scalable storage
- **Caching:** Redis-backed query caching and rate limiting
- **Observability:** Prometheus metrics + OpenTelemetry traces
- **Migrations:** Alembic for versioned schema changes

## 🚀 Quick Start

### Option 1: Local Development (Fastest)

```bash
# Clone and setup
git clone https://github.com/bbrysonelite-max/Mini-RAG.git
cd Mini-RAG

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
bash START_LOCAL.sh
```

Open http://localhost:8000/app in your browser.

### Option 2: Docker Compose

```bash
# Full stack with PostgreSQL + Redis
docker-compose up --build

# Wait for health check
curl http://localhost:8000/health
```

### Option 3: One-Click Deploy

```bash
./scripts/one_click_deploy.sh [heroku|fly|render|railway]
```

## 📖 Usage

### 1. Ingest Documents

**Via Web UI:**
1. Go to the **Ingest** tab
2. Drag & drop files or paste YouTube URLs
3. Watch the progress indicator

**Via CLI:**
```bash
python raglite.py ingest-docs --path document.pdf
python raglite.py ingest-youtube --url https://youtube.com/watch?v=...
python raglite.py ingest-transcript --path transcript.vtt
```

### 2. Ask Questions

Go to the **Ask** tab and query your knowledge base:
- "What are the main points from the uploaded documents?"
- "Summarize the key insights from the YouTube video"

### 3. Use Commands

Select a command from the dropdown:
- **Build Prompt:** Create AI prompts from your knowledge
- **Build Workflow:** Design step-by-step processes
- **Build Customer Avatar:** Define target customer profiles
- **Build Expert Instructions:** Create specialized AI personas

### 4. Save Assets

Click **Save** on any command output to store it as a reusable asset in the **Assets** tab.

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘/Ctrl + K` | Focus search/ask |
| `⌘/Ctrl + I` | Go to Ingest |
| `⌘/Ctrl + S` | Go to Sources |
| `⌘/Ctrl + A` | Go to Assets |
| `⌘/Ctrl + ,` | Go to Admin |
| `Escape` | Close modal |
| `?` | Show all shortcuts |

## 🏗️ Architecture

```
second-brain/
├── server.py              # FastAPI backend
├── rag_pipeline.py        # RAG orchestration
├── database.py            # PostgreSQL + pgvector
├── vector_store.py        # Embedding storage
├── model_service.py       # LLM providers (OpenAI, Anthropic)
├── frontend-react/        # React UI
│   ├── src/components/    # UI components
│   │   ├── Toast.tsx      # Notifications
│   │   ├── Skeleton.tsx   # Loading states
│   │   ├── EmptyState.tsx # Empty states
│   │   └── ...
│   └── src/hooks/         # Custom hooks
│       ├── useToast.ts
│       └── useKeyboardShortcuts.ts
├── alembic/               # Database migrations
└── scripts/               # Deployment & utilities
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=your-secret-key
OPENAI_API_KEY=sk-...

# Optional
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://localhost:6379/0
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Development
LOCAL_MODE=true
ALLOW_INSECURE_DEFAULTS=true
```

### Database Setup

```bash
# Initialize schema
psql $DATABASE_URL < db_schema.sql

# Run migrations
python scripts/run_migrations.py upgrade
```

## 📊 API Endpoints

### Core APIs
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ask` | Query the knowledge base |
| `POST` | `/api/v1/ingest/urls` | Ingest YouTube URLs |
| `POST` | `/api/v1/ingest/files` | Upload and ingest files |
| `GET` | `/api/v1/sources` | List all sources |
| `GET` | `/api/v1/workspaces/{id}/assets` | List saved assets |
| `GET` | `/api/v1/workspaces/{id}/history` | View command history |

### Admin APIs
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/api/v1/admin/stats` | System statistics |

Full API documentation at `/docs` (Swagger UI).

## 🔒 Security

- **Authentication:** OAuth 2.0 + JWT tokens + API keys
- **Authorization:** Role-based access (viewer, editor, admin, owner)
- **Input Validation:** SQL injection & XSS prevention
- **CSRF Protection:** Token-based protection
- **Security Headers:** CSP, X-Frame-Options, etc.
- **Audit Logging:** All security events logged

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_rag_pipeline.py -v
```

## 📈 Monitoring

### Prometheus Metrics
- `http_requests_total` - Request count by endpoint
- `http_request_duration_seconds` - Latency histograms
- `rag_chunks_total` - Total chunks in index
- `rag_queries_total` - Query count

### Health Endpoint
```bash
curl http://localhost:8000/health
# {"status": "healthy", "database": "healthy", "chunks_count": 79}
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [START_HERE.md](START_HERE.md) | First-time setup guide |
| [QUICK_START.md](🚀_QUICK_START.md) | Quick start reference |
| [UI_UX_IMPROVEMENTS_COMPLETE.md](UI_UX_IMPROVEMENTS_COMPLETE.md) | UI/UX changelog |
| [DATABASE_HARDENING_COMPLETE.md](DATABASE_HARDENING_COMPLETE.md) | Database improvements |
| [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) | Production checklist |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built with ❤️ for knowledge workers who want AI-powered second brains.**
