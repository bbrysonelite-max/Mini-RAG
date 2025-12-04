# Check Railway Deployment

## Quick Check

1. **Open Railway Dashboard**: https://railway.app/project/960ca9b9-2b01-47b7-9ad5-bdd081327f15
2. **Check Deployments Tab** - Should show recent deployments
3. **Check if GitHub is connected**:
   - Settings → GitHub
   - Should show: `bbrysonelite-max/Mini-RAG`
   - Auto-deploy should be ON

## If No Auto-Deploy

Railway might not be watching GitHub. Options:

### Option A: Manual Deploy via CLI
```bash
railway up
```

### Option B: Manual Deploy via Dashboard
1. Railway Dashboard → Your Service
2. Click "Deploy" or "Redeploy" button
3. Select latest commit

### Option C: Reconnect GitHub
1. Settings → GitHub → Disconnect
2. Reconnect → Select repo
3. Enable auto-deploy for `main` branch

## Current Commits Pushed
- `c80d346` - Add database deduplication
- `318d5fd` - Make pgvector optional
- `55ac510` - Make pgvector optional for Railway

These should trigger a deploy if GitHub is connected.



