# Testing Railway Chunk Persistence

## The Issue

The `.railway.internal` hostname only works **inside Railway's network**, not from your local machine. We can't test the Railway database directly from your Mac.

## How to Test Persistence

### Method 1: Check Railway Logs (Easiest)

After Railway redeploys, check the logs for chunk loading:

```bash
railway logs --tail 100 | grep -i "chunks\|database\|schema"
```

Look for:
- ✅ "Loaded X chunks from database" 
- ✅ "Database schema initialized successfully"
- ✅ "Successfully persisted X chunks to database"

### Method 2: Check Health Endpoint

Once Railway is deployed, check the health endpoint:

```bash
# Get your Railway app URL
railway domain

# Or check Railway dashboard for the URL
curl https://your-app.railway.app/health
```

The health endpoint should show `chunks_count` - if it shows chunks after redeploy, persistence is working!

### Method 3: Upload via Railway App

1. Go to your Railway app URL: `https://your-app.railway.app/app`
2. Upload a test file
3. Check logs: `railway logs | grep "persisted"`
4. Trigger a redeploy (change something minor)
5. Check if chunks still exist after redeploy

### Method 4: Check Database Directly (Inside Railway)

Run a query inside Railway's network:

```bash
railway run --service Mini-RAG python3 -c "
import os, asyncio
from database import init_database
from vector_store import VectorStore

async def check():
    db = await init_database(os.getenv('DATABASE_URL'), init_schema=False)
    store = VectorStore(db)
    chunks = await store.fetch_all_chunks()
    print(f'Found {len(chunks)} chunks in database')

asyncio.run(check())
"
```

## Expected Result

✅ **Chunks should persist** because:
- They're stored in PostgreSQL (persistent)
- Code loads chunks from database on startup if file doesn't exist
- Database survives redeploys (it's a separate Railway service)

## Current Status

- ✅ Code pushed to GitHub
- ⏳ Railway deployment in progress
- ⏳ Waiting for deployment to complete
- ⏳ Then verify chunks persist


