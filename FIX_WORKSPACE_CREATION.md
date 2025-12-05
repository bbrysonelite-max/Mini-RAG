# Fix: Cannot Create Workspaces

## Problem
Workspace creation fails when clicking "Create New Workspace" in the UI.

## Root Cause
Database tables for workspace management don't exist or weren't created properly.

## Solution

### Step 1: Check if Database is Configured
```bash
echo $DATABASE_URL
```

If empty, you need to set it.

### Step 2: Create Missing Tables
Run the database schema:

```bash
# Option A: Direct SQL
psql $DATABASE_URL < db_schema.sql

# Option B: Using Alembic migrations  
alembic upgrade head
```

### Step 3: Verify Tables Exist
```bash
psql $DATABASE_URL -c "\dt"
```

Required tables:
- ✅ organizations
- ✅ workspaces
- ✅ workspace_members
- ✅ workspace_settings
- ✅ user_organizations
- ✅ users

### Step 4: Test Workspace Creation
```bash
# Test API directly
curl -X POST http://localhost:8000/api/v1/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Workspace"}'
```

Should return:
```json
{
  "workspace": {
    "id": "...",
    "name": "Test Workspace",
    "slug": "test-workspace",
    ...
  }
}
```

### Step 5: Check for Errors
If still failing, check logs:
```bash
tail -f logs/rag.log
```

Common errors:
- **"Database not configured"** → Set DATABASE_URL
- **"relation 'workspaces' does not exist"** → Run db_schema.sql
- **"User ID not found"** → Set LOCAL_MODE=true for development

## Quick Fix for LOCAL_MODE
If you're in development mode:

```bash
export LOCAL_MODE=true
```

This bypasses authentication and uses a default organization.

## Verification
1. Start server: `python server.py` or `uvicorn server:app`
2. Open http://localhost:8000/app/
3. Click workspace dropdown → "Create New Workspace"
4. Enter name → Click "Create"
5. Should see new workspace in dropdown

## If Still Not Working
Check browser console (Cmd+Option+J on Mac Chrome) for errors like:
- 503: Database not configured
- 500: SQL errors (tables missing)
- 401: Authentication issues (set LOCAL_MODE=true)


