# 🚀 START HERE - Second Brain Setup Guide

Welcome to Second Brain! This guide will get you up and running in minutes.

---

## Quick Start Options

### Option 1: Local Development (Recommended for First-Time)

```bash
# 1. Clone the repo
git clone https://github.com/bbrysonelite-max/Mini-RAG.git
cd Mini-RAG

# 2. Run the setup script
bash START_LOCAL.sh

# 3. Open in browser
open http://localhost:8000/app
```

That's it! The server will start in LOCAL_MODE with default settings.

---

### Option 2: Full Production Setup

```bash
# 1. Copy environment template
cp env.template .env

# 2. Edit .env with your credentials:
#    - DATABASE_URL (PostgreSQL with pgvector)
#    - SECRET_KEY (generate with: openssl rand -hex 32)
#    - OPENAI_API_KEY or ANTHROPIC_API_KEY
#    - GOOGLE_CLIENT_ID/SECRET (for OAuth)
#    - STRIPE_SECRET_KEY (for billing)

# 3. Initialize database
psql $DATABASE_URL < db_schema.sql

# 4. Start with production settings
LOCAL_MODE=false bash START_LOCAL.sh
```

---

## What Can You Do?

### 1. **Ingest Documents** (Ingest Tab)
- Drag & drop PDFs, Word docs, Markdown, images
- Paste YouTube URLs for video transcripts
- Paste raw text directly

### 2. **Ask Questions** (Ask Tab)
- Query your knowledge base in natural language
- Get AI-powered answers with citations
- Use commands like "Build Prompt" or "Build Workflow"

### 3. **View Sources** (Sources Tab)
- See all ingested documents
- Filter by type, name, or date
- Track chunk counts per source

### 4. **Save Assets** (Assets Tab)
- Save command outputs as reusable templates
- Organize prompts, workflows, avatars
- Build your prompt library

### 5. **Track History** (History Tab)
- View past commands and outputs
- Re-run successful queries
- Save outputs to Assets

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘/Ctrl + K` | Focus search |
| `⌘/Ctrl + I` | Go to Ingest |
| `⌘/Ctrl + S` | Go to Sources |
| `⌘/Ctrl + A` | Go to Assets |
| `?` | Show all shortcuts |

---

## 🔧 Configuration Reference

### Required Environment Variables

```bash
# Database (PostgreSQL with pgvector)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Security
SECRET_KEY=your-256-bit-secret-key

# AI Provider (at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Optional Environment Variables

```bash
# Authentication
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Billing
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Caching
REDIS_URL=redis://localhost:6379/0

# Development
LOCAL_MODE=true              # Skip auth for local dev
ALLOW_INSECURE_DEFAULTS=true # Use placeholder secrets
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Full project overview |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [UI_UX_IMPROVEMENTS_COMPLETE.md](UI_UX_IMPROVEMENTS_COMPLETE.md) | UI/UX features |
| [DATABASE_HARDENING_COMPLETE.md](DATABASE_HARDENING_COMPLETE.md) | Database setup |
| [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) | Production checklist |

---

## 🆘 Troubleshooting

### Server won't start?
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process
pkill -f "uvicorn server:app"

# Try again
bash START_LOCAL.sh
```

### Database connection issues?
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check if pgvector is installed
psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname='vector'"
```

### Auth not working?
- Ensure `LOCAL_MODE=false` is set
- Verify Google OAuth credentials in `.env`
- Check redirect URIs in Google Cloud Console

---

## 🎯 Next Steps

1. **Ingest your first document** - Go to Ingest tab, upload a PDF
2. **Ask a question** - Go to Ask tab, query your document
3. **Save an asset** - Use a command, save the output
4. **Explore shortcuts** - Press `?` to see all keyboard shortcuts

**Happy building!** 🧠✨
