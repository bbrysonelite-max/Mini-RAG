# Starting the Server for Testing

## Quick Start

Open a **new terminal window** and run:

```bash
cd /Users/brentbryson/Desktop/mini-rag
source venv/bin/activate
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/rag_brain" uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

## What to Look For

You should see output like:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Once Server is Running

1. **Open browser**: http://localhost:8000/app
2. **Upload a test file** (PDF, TXT, MD, etc.)
3. **Verify chunks** were created:
   ```bash
   DATABASE_URL="postgresql://postgres:postgres@localhost:5432/rag_brain" python3 scripts/test_persistence.py
   ```

## If You See Database Connection Errors

Make sure Docker Compose database is running:
```bash
docker ps | grep mini-rag-db
```

If not running:
```bash
docker compose up db -d
```

