# Production Testing Plan

## Test 1: Database Schema ✅
- [x] Schema initializes without errors
- [ ] Verify tables exist in database

## Test 2: Chunk Persistence
- [ ] Upload a test file via UI
- [ ] Verify chunks created in database
- [ ] Check chunk count via API
- [ ] Trigger redeploy
- [ ] Verify chunks persist after redeploy

## Test 3: Query Functionality
- [ ] Ask a question about uploaded document
- [ ] Verify answer is returned
- [ ] Verify citations are included
- [ ] Verify answer quality

## Test 4: Error Handling
- [ ] Upload invalid file type → Should reject gracefully
- [ ] Upload oversized file → Should reject gracefully
- [ ] Query with no chunks → Should return helpful message

## Test 5: Health Checks
- [ ] `/health` endpoint returns correct status
- [ ] Database status is "healthy"
- [ ] Chunk count is accurate



