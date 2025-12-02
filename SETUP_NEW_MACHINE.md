# Setting Up Mini-RAG on a New Machine

This guide helps you set up Mini-RAG on a different computer or sync changes between multiple machines.

## Quick Setup (New Machine)

Run the automated setup script:

```bash
./setup_new_machine.sh
```

This script will:
- ✅ Check for required dependencies (Python, Node.js, npm)
- ✅ Create Python virtual environment
- ✅ Install Python dependencies
- ✅ Install and build frontend
- ✅ Create `.env` file from template
- ✅ Provide next steps

## Manual Setup Steps

If you prefer to set up manually:

### 1. Clone/Copy the Project

```bash
# If using Git:
git clone <your-repo-url>
cd mini-rag

# Or copy the folder to the new machine
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up Frontend

```bash
cd frontend-react
npm install
npm run build
cd ..
```

### 4. Configure Environment

```bash
# Copy template
cp PRODUCTION_ENV_TEMPLATE .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required in `.env`:**
- `OPENAI_API_KEY` - Required for LLM features
- `SECRET_KEY` - Generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- `LOCAL_MODE=true` - For local development (bypasses auth)

**Optional:**
- `DATABASE_URL` - PostgreSQL connection string
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - For Google OAuth
- `ANTHROPIC_API_KEY` - For Claude models

### 5. Set Up Database (Optional)

**Option A: Docker Compose**
```bash
docker-compose up -d
docker exec -i mini-rag-db psql -U postgres -d rag_brain < db_schema.sql
```

**Option B: Local PostgreSQL**
```bash
# Create database
createdb rag_brain

# Initialize schema
psql rag_brain < db_schema.sql
```

**Option C: Remote Database**
- Point `DATABASE_URL` in `.env` to your remote PostgreSQL instance
- Run: `psql $DATABASE_URL < db_schema.sql`

### 6. Start the Server

```bash
./START_LOCAL.sh
```

Or manually:
```bash
source venv/bin/activate
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Open: http://localhost:8000/app

## Syncing Between Machines

### Using Git (Recommended)

**On Machine A (make changes):**
```bash
git add .
git commit -m "Your changes"
git push
```

**On Machine B (get changes):**
```bash
git pull
# Rebuild frontend if needed
cd frontend-react && npm run build && cd ..
```

### What to Sync

**✅ Sync via Git:**
- All code files
- Configuration files (except `.env`)
- Database schema (`db_schema.sql`)

**❌ Don't Sync (Machine-Specific):**
- `.env` file (contains secrets, copy manually)
- `venv/` folder (recreate on each machine)
- `node_modules/` folder (reinstall on each machine)
- Database data (unless using shared remote database)

### Sharing `.env` Securely

**Option 1: Manual Copy**
- Copy `.env` file securely (encrypted transfer, USB drive, etc.)
- Never commit `.env` to Git (it's in `.gitignore`)

**Option 2: Environment Variables Template**
- Keep a `.env.example` file with placeholder values
- Document required variables in README

**Option 3: Secret Management**
- Use a password manager or secret sharing service
- Store API keys securely and recreate `.env` on each machine

## Database Sync Options

### Option 1: Separate Databases (Default)
- Each machine has its own local database
- **Ingested documents, chunks, and embeddings are NOT shared**
- Workspaces, assets, and history are machine-specific
- You must ingest documents separately on each machine
- Good for: Independent development, testing different configurations

### Option 2: Shared Remote Database (Recommended for Data Sync)
- Point both machines to the same `DATABASE_URL` in `.env`
- **All ingested data IS shared automatically**
- Workspaces, assets, history, documents, and chunks sync automatically
- Ingest on one machine → available on the other immediately
- Good for: Team collaboration, keeping data in sync, production use

**To set up shared database:**
```bash
# On both machines, edit .env:
DATABASE_URL=postgresql://user:password@your-db-host:5432/rag_brain

# Initialize schema (only needed once):
psql $DATABASE_URL < db_schema.sql
```

### Option 3: Database Dumps (One-Time Sync)
```bash
# Export from Machine A
pg_dump $DATABASE_URL > backup.sql

# Import to Machine B
psql $DATABASE_URL < backup.sql
```
**Note:** This is a one-time copy. For ongoing sync, use Option 2 (shared database).

### Important: What Gets Synced

**With Shared Database (`DATABASE_URL`):**
- ✅ All ingested documents and chunks
- ✅ Vector embeddings
- ✅ Workspaces and workspace settings
- ✅ Assets (prompts, workflows, etc.)
- ✅ History (command interactions)
- ✅ Users and organizations

**Without Shared Database:**
- ❌ Each machine has separate data
- ❌ Must ingest documents on each machine
- ❌ Workspaces and assets are independent

## Troubleshooting

### "Module not found" errors
```bash
# Reinstall Python dependencies
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend not updating
```bash
# Rebuild frontend
cd frontend-react
npm install
npm run build
cd ..
```

### Database connection errors
- Check `DATABASE_URL` in `.env`
- Ensure PostgreSQL is running
- Verify network connectivity (for remote databases)

### Port already in use
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or use a different port
# Edit START_LOCAL.sh or use: --port 8001
```

## Requirements Checklist

Before running setup, ensure you have:

- ✅ Python 3.8+ (`python3 --version`)
- ✅ Node.js 16+ (`node --version`)
- ✅ npm (`npm --version`)
- ✅ PostgreSQL (optional, for persistence)
- ✅ Git (optional, for syncing)

## Quick Reference

```bash
# Setup new machine
./setup_new_machine.sh

# Start server
./START_LOCAL.sh

# Sync code (Machine A → Machine B)
git push    # On Machine A
git pull    # On Machine B

# Rebuild after sync
cd frontend-react && npm run build && cd ..
```

## Need Help?

- Check `README.md` for detailed documentation
- Review `START_LOCAL.sh` for startup options
- See `db_schema.sql` for database structure

