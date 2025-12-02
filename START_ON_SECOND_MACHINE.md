# Starting Mini-RAG on a Second Machine

This guide walks you through getting Mini-RAG running on your second machine and connecting it to your shared database.

## Prerequisites

- Second machine has Python 3.8+, Node.js 16+, and npm installed
- You have access to the shared database (DATABASE_URL)
- You have the project code (via Git or file copy)

---

## Step-by-Step Setup

### Step 1: Get the Code on Second Machine

**Option A: Using Git (Recommended)**
```bash
# Clone the repository
git clone <your-repo-url>
cd mini-rag

# Or if you already have it, pull latest changes
cd mini-rag
git pull
```

**Option B: Copy Files**
- Copy the entire `mini-rag` folder to the second machine
- Use USB drive, network share, or cloud storage

### Step 2: Run the Setup Script

```bash
cd mini-rag
./setup_new_machine.sh
```

This will:
- ✅ Check dependencies
- ✅ Create Python virtual environment
- ✅ Install Python packages
- ✅ Install and build frontend
- ✅ Create `.env` file

### Step 3: Configure Database Connection

**Edit `.env` file:**
```bash
nano .env  # or use your preferred editor
```

**Set the DATABASE_URL** to point to your shared database:

**If using Docker Compose on Machine A:**
```bash
# Replace 192.168.1.100 with Machine A's IP address
DATABASE_URL=postgresql://postgres:postgres@192.168.1.100:5432/rag_brain
```

**If using cloud database (Railway, Supabase, etc.):**
```bash
DATABASE_URL=postgresql://user:password@hostname:5432/dbname
```

**Or use the helper script:**
```bash
./scripts/setup_shared_db.sh
# Choose option 2 (cloud database) or option 3 (local PostgreSQL)
# Paste your DATABASE_URL when prompted
```

### Step 4: Configure Other Required Settings

**Edit `.env` and set:**
```bash
# Required for LLM features
OPENAI_API_KEY=sk-your-openai-key-here

# For local development (bypasses authentication)
LOCAL_MODE=true
ALLOW_INSECURE_DEFAULTS=true

# Generate a new SECRET_KEY (or reuse from Machine A)
SECRET_KEY=your-secret-key-here
# Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Optional: Google OAuth (if using)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Step 5: Initialize Database Schema (If Not Done Already)

**Only needed once** - if Machine A already initialized it, skip this step.

```bash
# Test connection first
psql $DATABASE_URL -c "SELECT version();"

# Initialize schema
psql $DATABASE_URL < db_schema.sql
```

### Step 6: Start the Server

```bash
./START_LOCAL.sh
```

Or manually:
```bash
source venv/bin/activate
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### Step 7: Access the Application

Open your browser:
- **Web UI:** http://localhost:8000/app
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## Quick Verification Checklist

After starting, verify everything works:

- [ ] Server starts without errors
- [ ] Can access http://localhost:8000/app
- [ ] Can see workspaces (if any exist in shared database)
- [ ] Can ingest a document
- [ ] Document appears on both machines

---

## Troubleshooting

### "Module not found" errors
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend not loading
```bash
cd frontend-react
npm install
npm run build
cd ..
```

### Database connection errors
```bash
# Test connection
psql $DATABASE_URL -c "SELECT version();"

# Check .env file
cat .env | grep DATABASE_URL

# Verify database is accessible from this machine
ping <database-host-ip>
```

### Port already in use
```bash
# Find what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or use a different port:
# Edit START_LOCAL.sh and change --port 8000 to --port 8001
```

### "No such file or directory" for scripts
```bash
# Make scripts executable
chmod +x setup_new_machine.sh
chmod +x START_LOCAL.sh
chmod +x scripts/*.sh
```

---

## What Gets Synced?

Once both machines use the same `DATABASE_URL`, these sync automatically:

- ✅ **Workspaces** - Create on one, see on both
- ✅ **Documents** - Ingest on one, available on both
- ✅ **Chunks & Embeddings** - All vector data shared
- ✅ **Assets** - Prompts, workflows, pages, etc.
- ✅ **History** - Command interactions
- ✅ **Users** - User accounts and permissions

**Not synced** (machine-specific):
- ❌ `.env` file (must configure separately)
- ❌ `venv/` folder (recreated on each machine)
- ❌ `node_modules/` (reinstalled on each machine)

---

## Quick Reference Commands

```bash
# Full setup (first time)
./setup_new_machine.sh
./scripts/setup_shared_db.sh  # Configure DATABASE_URL
psql $DATABASE_URL < db_schema.sql  # Initialize schema (once)

# Start server
./START_LOCAL.sh

# Stop server
# Press Ctrl+C in the terminal

# Update code (if using Git)
git pull
cd frontend-react && npm run build && cd ..
```

---

## Next Steps

1. **Test data sync:** Ingest a document on Machine A, verify it appears on Machine B
2. **Create a workspace:** Create on one machine, verify it's on both
3. **Test Ask command:** Query on one machine, verify history appears on both

You're all set! Both machines are now sharing the same database and data.

