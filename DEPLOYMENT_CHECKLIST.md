# Railway Deployment Checklist

## Current Deployment Status

✅ **Deployment Triggered**: Railway is building/deploying now
🔗 **Build Logs**: https://railway.com/project/960ca9b9-2b01-47b7-9ad5-bdd081327f15/service/b8c184a2-1467-4817-b2dd-0e1232f7d14a

## Issues to Watch For

### 1. Database Schema Not Initialized
**Symptom**: `relation "workspace_members" does not exist`

**Fix**: The code has `init_schema=True` in startup, but if DATABASE_URL is incomplete or connection fails, schema won't initialize.

**Check**: Railway → Your Service → Variables → Verify `DATABASE_URL` is set correctly

### 2. DATABASE_URL Configuration
**Current**: Shows as `postgresql://` (might be incomplete)

**Action**: 
1. Go to Railway → Your Postgres Service
2. Copy the full `DATABASE_URL` or `DATABASE_PUBLIC_URL`
3. Set it in Railway → Your App Service → Variables

### 3. Schema Initialization
If schema fails to auto-initialize, manually run:
```bash
# Get Railway DATABASE_URL
railway variables

# Run schema initialization
railway run python scripts/init_railway_db.py
```

## After Deployment Completes

1. **Check Health**: `curl https://your-railway-url.railway.app/health`
2. **Test Chunk Persistence**:
   ```bash
   DATABASE_URL="railway_database_url" python3 scripts/test_persistence.py
   ```
3. **Expected**: Should show 27+ chunks persisted

## Monitoring Deployment

Watch logs:
```bash
railway logs --tail 50
```

Look for:
- ✅ "Database schema initialized successfully"
- ✅ "Database initialized successfully"  
- ❌ Any database connection errors
- ❌ Schema initialization failures


