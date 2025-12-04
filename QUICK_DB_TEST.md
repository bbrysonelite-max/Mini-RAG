# Quick Database Test Guide

## Issue: `python` command not found

Your system uses `python3`, not `python`. Here's how to test the database:

## Option 1: Use Python3 Directly

```bash
# 1. Get your Railway DATABASE_URL
#    Go to Railway dashboard → Your Postgres service → Copy "Public URL"

# 2. Set the DATABASE_URL
export DATABASE_URL="postgresql://user:password@host:port/database"

# 3. Run the test script
python3 scripts/test_database.py
```

## Option 2: Use Virtual Environment

```bash
# 1. Activate your virtual environment
source venv/bin/activate

# 2. Set DATABASE_URL (get from Railway dashboard)
export DATABASE_URL="postgresql://user:password@host:port/database"

# 3. Run the test script
python scripts/test_database.py
```

## Option 3: Use the Helper Script

```bash
# 1. Set DATABASE_URL first
export DATABASE_URL="postgresql://user:password@host:port/database"

# 2. Run the helper script
./scripts/test_db_simple.sh
```

## Getting Your Railway DATABASE_URL

1. Go to https://railway.app
2. Select your project
3. Click on your **Postgres** service
4. Go to the **Variables** or **Connect** tab
5. Copy the **`DATABASE_URL`** or **`DATABASE_PUBLIC_URL`** value

Or use Railway CLI:
```bash
railway variables
# Look for DATABASE_URL
```

## What the Test Does

The test script will:
- ✅ Verify database connection
- ✅ Check pgvector extension
- ✅ Validate schema tables exist
- ✅ Test vector store initialization
- ✅ Report chunk counts
- ✅ Perform health checks

## Common Issues

### "psql: command not found"
This is fine - you don't need `psql` for the Python test script.

### "ModuleNotFoundError: No module named 'psycopg'"
Install dependencies:
```bash
source venv/bin/activate
pip install psycopg[binary] psycopg-pool
```

### "DATABASE_URL not set"
Make sure you export it:
```bash
export DATABASE_URL="your_actual_url_here"
```



