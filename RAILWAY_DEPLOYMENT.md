# Railway Deployment Guide

## Current Status

✅ Code pushed to GitHub: `fe240b4` - "Test chunk persistence"

## Railway Auto-Deploy

Railway should automatically deploy when you push to `main` branch IF:
1. Railway project is connected to your GitHub repo
2. Railway is watching the `main` branch
3. Railway service is active

## Check Railway Deployment

1. **Go to Railway Dashboard**: https://railway.app
2. **Select your project** (Mini-RAG)
3. **Check Deployments tab** - should show a new deployment starting
4. **Check Logs** - watch for build/deploy progress

## If Railway Isn't Deploying

### Option 1: Manual Trigger
1. Go to Railway dashboard
2. Click on your service
3. Click "Deploy" or "Redeploy" button

### Option 2: Check Railway Connection
1. Railway → Project → Settings
2. Verify GitHub repo is connected
3. Check which branch Railway is watching (should be `main`)

### Option 3: Check Railway Service Status
1. Railway → Project → Your Service
2. Verify service is not paused/stopped
3. Check if there are any errors

## After Deployment Completes

Test chunk persistence:
```bash
# Get Railway DATABASE_URL from Railway dashboard
DATABASE_URL="your_railway_database_url" python3 scripts/test_persistence.py
```

Expected: Should show 27+ chunks persisted in Railway's PostgreSQL database.

