# Fix Railway Deployment Spam

## Problem
You have 8 Railway projects, all triggering deploys on every GitHub push.

## Projects Found
```
1. zippy-reflection
2. alert-passion ← CURRENT (keep this one)
3. industrious-caring
4. sweet-delight
5. strong-renewal
6. alert-vision
7. glistening-grace
8. industrious-caring
9. imaginative-serenity
```

## Solution: Delete Old Projects

### Step 1: Go to Railway Dashboard
https://railway.app/dashboard

### Step 2: Delete Each Unused Project
For EACH project EXCEPT `alert-passion`:

1. Click on the project
2. Go to **Settings** (gear icon)
3. Scroll to bottom
4. Click **"Delete Project"**
5. Confirm deletion

### Step 3: Verify Only One Project Remains
After deleting all except `alert-passion`:
```bash
railway list
```

Should show only:
```
Brent Bryson's Projects
  alert-passion
```

## Quick Delete Commands

You can also use Railway CLI to delete them:
```bash
# Switch to each project and delete it
railway link
# Select the project to delete, then:
railway project delete
```

Repeat for each unwanted project.

## After Cleanup

1. Verify auto-deploy on `alert-passion`:
   - https://railway.app/project/{your-project-id}/settings
   - GitHub section should show: `bbrysonelite-max/Mini-RAG`
   - Auto Deploy: ON

2. Test with one push:
   ```bash
   git commit --allow-empty -m "Test single deploy"
   git push
   ```

You should get ONE email, not 10.

## Production URL
After cleanup, your app will be at:
https://mini-rag-production.up.railway.app
