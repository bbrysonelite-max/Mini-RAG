# PROJECT CLEANUP PLAN

## Current State (THE MESS)
- 343+ markdown files
- 4,576 lines in server.py (should be ~500)
- 30+ redundant "DONE/COMPLETE/SUCCESS" files
- 6+ duplicate Railway deployment docs
- Multiple test reports with same info
- Scattered scripts with duplicate functionality

## PHASE 1: DELETE REDUNDANT DOCUMENTATION (Priority 1)

### Status Files to DELETE (all say the same thing)
- [ ] DONE.md
- [ ] PROJECT_COMPLETE.md  
- [ ] STEP2_COMPLETE.md
- [ ] COMPLETION_SUMMARY.md
- [ ] DATABASE_HARDENING_COMPLETE.md
- [ ] PERSISTENCE_SUCCESS.md
- [ ] TESTING_COMPLETE.md
- [ ] UI_UX_IMPROVEMENTS_COMPLETE.md
- [ ] ✅_READY_FOR_CUSTOMERS.md
- [ ] 📦_DELIVERY_COMPLETE.md
- [ ] GO_LIVE_NOW.md
- [ ] LAUNCH_ANNOUNCEMENT.md
- [ ] PROGRESS_SUMMARY.md

### Railway/Deployment Docs to CONSOLIDATE (6 files → 1)
Keep: DEPLOYMENT.md (create new, simple)
Delete:
- [ ] RAILWAY_DEPLOYMENT.md
- [ ] RAILWAY_DEPLOYMENT_FIX.md
- [ ] RAILWAY_AUTO_DEPLOY_FIX.md
- [ ] RAILWAY_EMERGENCY_FIX.md
- [ ] FIX_RAILWAY_DEPLOY.md
- [ ] FIX_RAILWAY_SPAM.md
- [ ] CHECK_RAILWAY.md
- [ ] MANUAL_DEPLOY_STEPS.md
- [ ] DEPLOYMENT_CHECKLIST.md
- [ ] DEPLOYMENT_STATUS.md

### Test Documentation to CONSOLIDATE (7 files → 1)
Keep: TESTING.md (create new)
Delete:
- [ ] TEST_REPORT.md
- [ ] TEST_RESULTS.md
- [ ] TEST_SUMMARY.md
- [ ] FINAL_TEST_REPORT.md
- [ ] TEST_PLAN.md
- [ ] TEST_RAILWAY_PERSISTENCE.md
- [ ] TEST_PERSISTENCE.md
- [ ] QUICK_DB_TEST.md
- [ ] BRUTAL_TRUTH_FINAL_ASSESSMENT.md

### Database Docs to CONSOLIDATE (5 files → 1)
Keep: DATABASE.md (create new)
Delete:
- [ ] DATABASE_FIXES.md
- [ ] DATABASE_PERSISTENCE_BUGS.md
- [ ] PGVECTOR_SETUP.md
- [ ] SHARED_DATABASE_SETUP.md
- [ ] LOCAL_VS_RAILWAY.md

### Setup Docs to CONSOLIDATE (5 files → 1)
Keep: SETUP.md (create new)
Delete:
- [ ] START_HERE.md
- [ ] START_SERVER.md
- [ ] START_ON_SECOND_MACHINE.md
- [ ] SETUP_NEW_MACHINE.md
- [ ] SIMPLE_SECOND_MACHINE_SETUP.md
- [ ] QUICK_SETUP_SECOND_MACHINE.md
- [ ] 🚀_QUICK_START.md

### Misc Redundant Files
- [ ] COMPREHENSIVE_FIX_PLAN.md
- [ ] QUICK_FIX_SUMMARY.md
- [ ] LAUNCH_CHECKLIST.md
- [ ] FIX_GOOGLE_LOGIN.md
- [ ] BROWSER_DEBUG_INSTRUCTIONS.md

**Total to DELETE: ~50 markdown files**

## PHASE 2: REFACTOR SERVER.PY (Priority 1)

### Current: 4,576 lines in ONE file
### Target: ~500 lines in server.py + modules

Split into:
- [ ] routes/health.py - Health/metrics endpoints
- [ ] routes/ingest.py - File upload/ingestion
- [ ] routes/query.py - Ask/query endpoints  
- [ ] routes/auth.py - Authentication endpoints
- [ ] routes/admin.py - Admin endpoints
- [ ] middleware.py - All middleware (CORS, rate limit, etc)
- [ ] app_factory.py - App initialization logic

## PHASE 3: CLEAN UP RAILWAY DEPLOYMENT (Priority 1)

Problems identified:
- Railway deploying from multiple projects
- Duplicate deployment scripts
- Unclear deployment process

Fix:
- [ ] Single railway.json config
- [ ] Remove duplicate scripts
- [ ] Clear documentation on Railway setup
- [ ] Test deployment works

## PHASE 4: CONSOLIDATE SCRIPTS

### Keep Only Essential Scripts
- [ ] scripts/start_server.sh
- [ ] scripts/run_tests.sh
- [ ] scripts/ingest_file.py

### Delete Redundant Scripts
- [ ] All test_*.sh files (use pytest)
- [ ] Duplicate deployment scripts
- [ ] One-off fix scripts

## PHASE 5: FINAL STRUCTURE

```
mini-rag/
├── README.md (clean, simple)
├── SETUP.md (one source of truth)
├── DEPLOYMENT.md (one source of truth)
├── server.py (~500 lines)
├── routes/ (new)
│   ├── health.py
│   ├── ingest.py
│   ├── query.py
│   └── auth.py
├── services/ (existing, keep)
├── tests/ (keep)
├── scripts/ (minimal, essential only)
└── docs/ (architecture, API reference only)
```

## SUCCESS CRITERIA

- [ ] < 20 markdown files in root
- [ ] server.py < 600 lines
- [ ] Clear, single source of truth for setup/deployment
- [ ] All tests still pass
- [ ] Railway deployment works

## EXECUTION ORDER

1. DELETE redundant docs (safe, reversible via git)
2. TEST core functionality still works
3. REFACTOR server.py into modules
4. TEST again
5. Clean up scripts
6. Create new consolidated docs
7. Final test + deployment verification

