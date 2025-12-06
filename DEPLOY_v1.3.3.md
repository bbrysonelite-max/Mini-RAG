# Deploy v1.3.3 - Instructions

**Status:** Ready to deploy
**Date:** 2025-12-06
**Commit:** 73f2a08

---

## What's in v1.3.3

### Critical RAG Fixes (From Debug Council PDF)
✅ **Fix 1: ID Wiring Restoration** - BM25 now returns chunk IDs (the 7-line fix)
✅ **Automatic JSONL Fallback** - If database empty, loads from file
✅ **Softer LLM Prompts** - Synthesizes instead of refusing
✅ **Lower Abstention Threshold** - 0.3 → 0.1

### Production Stability Fixes
✅ **UUID Error Fix** - Handles LOCAL_MODE user in workspace creation
✅ **Async Error Fix** - Fixed _count_lines coroutine issue
✅ **SECRET_KEY Auto-gen** - Generates temp key if not configured
✅ **Healthcheck Timeout** - Increased to 120s

### Process Improvements
✅ **Mandatory Version Control Rule** - Every commit must bump version
✅ **5 Debug Agents Created** - For systematic troubleshooting
✅ **Comprehensive Documentation** - Pipeline map, debug logs, status reports

---

## How to Deploy

### In your terminal, run:

```bash
cd /Users/brentbryson/Desktop/mini-rag
railway up
```

**Wait for:**
1. Build to complete (~2 minutes)
2. Deployment to succeed
3. Healthcheck to pass

---

## After Deployment - Verification Steps

### 1. Check Version
```bash
curl https://mini-rag-production.up.railway.app/version
```

**Expected:**
```json
{"version": "1.3.3", "build_date": "2025-12-06", "commit": "73f2a08"}
```

### 2. Check Health
```bash
curl https://mini-rag-production.up.railway.app/health
```

**Expected:**
- `status`: "healthy"
- `chunks_count`: >0 (should show 291 or similar)
- `llm_available`: true

### 3. Test RAG Answer
Go to: https://mini-rag-production.up.railway.app/app/

Ask a question about content in your knowledge base.

**Expected:** Substantive answer with citations (not "I don't have enough information")

### 4. Check UI Footer
Bottom of page should show: `Version 1.3.3 (73f2a08)`

If it shows old version, hard refresh browser (Cmd+Shift+R)

---

## If Anything Breaks

**Rollback:** Railway dashboard → previous deployment → "Redeploy"

**Debug:** Check Railway logs for errors

**Report:** Note the specific error, don't try to fix yourself

---

## What Comes Next (v1.4)

After thorough testing of v1.3.3:

### Priority Features (VERSION_1.4_TODO.md)
1. Enter key submits Ask query
2. Shift+Enter for multi-line
3. Settings panel improvements
4. Cohere reranking (if API key added)

**But first: TEST v1.3.3 thoroughly. Don't build new features on broken foundation.**

---

## Clean Start for Tomorrow

After deployment:
- ✅ Version control enforced
- ✅ Production and code in sync
- ✅ Known working version (1.3.3)
- ✅ Clear path forward (v1.4 TODO)
- ✅ All code committed and pushed

**You can test with confidence knowing exactly what version is running.**

