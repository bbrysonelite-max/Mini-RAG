# Local vs Railway - Codebase Comparison

## Are They the Same Codebase?

**Short Answer:** They SHOULD be the same codebase, but there are important differences:

### Code Source
- **Local:** Runs directly from `/Users/brentbryson/Desktop/mini-rag/`
- **Railway:** Deploys from GitHub `bbrysonelite-max/Mini-RAG` (main branch)
- **Sync Status:** Check with `git status` and `git log`

### Key Differences

#### 1. Environment Variables
**Local:**
- `DATABASE_URL`: `postgresql://postgres:postgres@localhost:5432/rag_brain` (Docker Compose)
- `LOCAL_MODE`: `true` (set in start script)
- `ALLOW_INSECURE_DEFAULTS`: `true`

**Railway:**
- `DATABASE_URL`: Railway PostgreSQL (different database)
- `LOCAL_MODE`: `true` (set in Railway variables)
- `ALLOW_INSECURE_DEFAULTS`: `false` (set in Railway variables)

#### 2. Database
- **Local:** Your local PostgreSQL (via Docker Compose or local install)
- **Railway:** Railway's managed PostgreSQL (separate database, separate data)

#### 3. Data Storage
- **Local:** Chunks stored in local database + `out/chunks.jsonl`
- **Railway:** Chunks stored in Railway database + `/app/data/chunks.jsonl` (container filesystem)

**⚠️ IMPORTANT:** These are SEPARATE databases with SEPARATE data!

### How to Verify They're in Sync

```bash
# Check if local has uncommitted changes
git status

# Check if local is ahead of GitHub
git log origin/main..HEAD

# Check if GitHub is ahead of local
git log HEAD..origin/main

# Check what Railway is running (check Railway dashboard or logs)
railway logs --tail 100 | grep "commit\|build"
```

### To Sync Them

**If local has changes Railway doesn't have:**
```bash
git add .
git commit -m "Your changes"
git push origin main
# Railway will auto-deploy (if connected) or manually: railway up
```

**If Railway has changes local doesn't have:**
```bash
git pull origin main
```

### Testing Both Environments

**Local Server:**
- URL: `http://localhost:8000`
- Database: Local PostgreSQL
- Data: Separate from Railway

**Railway Server:**
- URL: `https://mini-rag-production.up.railway.app`
- Database: Railway PostgreSQL  
- Data: Separate from local

**They are DIFFERENT instances with DIFFERENT data!**

### Current Status Check

Run these commands to verify:

```bash
# 1. Check local git status
git status

# 2. Check latest commits
git log --oneline -5

# 3. Check Railway deployment (if you have Railway CLI)
railway logs --tail 50 | grep -E "commit|build|Starting"
```

### Recommendation

**For testing:** Use Railway (production-like environment)
**For development:** Use local (faster iteration)

But remember: **They have separate databases and separate data!**


