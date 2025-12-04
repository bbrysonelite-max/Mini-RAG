# Railway Emergency Fix

## Critical Issues Found

### 1. Multiple Deploy Emails (10+ per push)
**Cause**: Two Railway config files (`railway.json` + `railway.toml`) conflicting

**Fix**: Deleted `railway.toml`, keeping only `railway.json`

### 2. "No LLM configured" Error
**Cause**: `OPENAI_API_KEY` not set in Railway environment variables

**Fix Now**:
1. Go to Railway Dashboard: https://railway.app/dashboard
2. Click your project → **Settings** → **Variables**
3. Add these variables:

```
OPENAI_API_KEY=sk-proj-your-actual-key-here
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here (optional)
DATABASE_URL=(should already be set by Railway Postgres)
```

### 3. Auto-Deploy Not Working
**Possible causes**:
- Multiple Railway services created (check dashboard for duplicates)
- GitHub webhook misconfigured
- Repository not properly linked

**Fix**:
1. Go to Railway Dashboard
2. Check if you see MULTIPLE services with similar names
3. If yes, **delete the old/duplicate ones**, keep only ONE
4. In the ONE service you keep:
   - Settings → Source
   - Verify: `bbrysonelite-max/Mini-RAG` on `main` branch
   - Enable "Auto Deploy"

### 4. Database Persistence
Once variables are set and only ONE service exists:
- Data should persist between deploys
- Check with: `https://your-app.railway.app/debug/db-status`

## Quick Action Items

1. ✅ Remove duplicate `railway.toml` (done)
2. ⏳ Set `OPENAI_API_KEY` in Railway Variables
3. ⏳ Delete duplicate Railway services (if any)
4. ⏳ Test with a simple push after cleanup

## Test After Fix

```bash
# Push this fix
git add -A
git commit -m "fix: remove duplicate railway.toml"
git push

# You should get ONLY ONE deploy email
```

