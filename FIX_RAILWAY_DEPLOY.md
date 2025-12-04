# Fix Railway Auto-Deploy

## Problem
Railway isn't auto-deploying when you push to GitHub.

## Solution: Check GitHub Connection

### Step 1: Open Railway Dashboard
1. Go to: https://railway.app/project/960ca9b9-2b01-47b7-9ad5-bdd081327f15
2. Click **Settings** (gear icon)

### Step 2: Check GitHub Integration
1. Look for **"GitHub"** or **"Source"** section
2. Check if it shows:
   - ✅ Connected to: `bbrysonelite-max/Mini-RAG`
   - ✅ Branch: `main`
   - ✅ Auto Deploy: **ON**

### Step 3: If Not Connected
1. Click **"Connect GitHub"** or **"Change Source"**
2. Select repository: `bbrysonelite-max/Mini-RAG`
3. Select branch: `main`
4. Enable **"Auto Deploy"**
5. Save

### Step 4: Manual Deploy (Quick Fix)
If you need to deploy now without fixing auto-deploy:

1. Railway Dashboard → Your Service (Mini-RAG)
2. Click **"Deploy"** or **"Redeploy"** button
3. Select commit: `1926e01 - Fix schema init: execute whole file instead of splitting statements`
4. Click **"Deploy"**

## Why Auto-Deploy Might Not Work

1. **GitHub not connected** - Most common issue
2. **Wrong branch** - Railway watching `master` instead of `main`
3. **Auto-deploy disabled** - Checked off in settings
4. **Railway service paused** - Service might be stopped

## Verify Connection

After connecting, push a test commit:
```bash
git commit --allow-empty -m "Test Railway auto-deploy"
git push origin main
```

Railway should start deploying within seconds.



