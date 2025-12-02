# Test Plan: Chunk Persistence Across Redeploys

## Goal
Verify that chunks stored in PostgreSQL survive Railway redeploys.

## Test Steps

### Step 1: Upload Test Documents (Local)
Upload some test documents to create chunks in the database.

### Step 2: Verify Chunks in Database
Check that chunks are stored in PostgreSQL (not just in files).

### Step 3: Deploy to Railway
Push code and trigger a Railway redeploy.

### Step 4: Verify Chunks Survived
After redeploy, check that chunks are still accessible.

## Expected Result
✅ Chunks should persist because they're stored in PostgreSQL (persistent), not in ephemeral container filesystem.


