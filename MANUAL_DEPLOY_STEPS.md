# Manual Railway Deployment Steps

## If Railway Isn't Auto-Deploying

### Step 1: Check Railway Dashboard
1. Go to: https://railway.app/project/960ca9b9-2b01-47b7-9ad5-bdd081327f15
2. Click on your **Mini-RAG** service
3. Check the **Deployments** tab
4. Look for recent deployments

### Step 2: Manual Deploy via Dashboard
1. In Railway Dashboard → Your Service
2. Click **"Deploy"** or **"Redeploy"** button (usually top right)
3. Select the latest commit: `c80d346 - Add database deduplication`
4. Click **"Deploy"**

### Step 3: Watch Build Logs
- Railway will show build progress
- Look for: "Building...", "Deploying...", "Success"

### Step 4: Verify Deployment
After deploy completes:
```bash
curl https://mini-rag-production.up.railway.app/health
```

Should show healthy status.

## Why Auto-Deploy Might Not Work

1. **GitHub not connected** - Railway needs to be linked to your GitHub repo
2. **Wrong branch** - Railway might be watching a different branch
3. **Auto-deploy disabled** - Check Settings → GitHub → Auto-deploy

## Quick Fix: Reconnect GitHub

1. Railway Dashboard → Project → **Settings**
2. **GitHub** section
3. If connected: Check "Auto Deploy" is ON
4. If not connected: Click "Connect GitHub" → Select repo → Enable auto-deploy


