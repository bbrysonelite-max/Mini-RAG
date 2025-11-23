# Mini-RAG Production Deployment Checklist

Use this checklist before deploying to staging or production environments.

## Pre-Deployment Validation

### 1. Environment Variables ✅
```bash
# Required - Authentication
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

# Required - Database
export DATABASE_URL="postgresql://user:password@host:port/rag_brain"

# Required - Stripe (use test keys for staging)
export STRIPE_API_KEY="sk_live_..."  # or sk_test_... for staging
export STRIPE_PRICE_ID="price_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
export STRIPE_SUCCESS_URL="https://yourdomain.com/billing/success"
export STRIPE_CANCEL_URL="https://yourdomain.com/billing/cancel"
export STRIPE_PORTAL_RETURN_URL="https://yourdomain.com/app"

# Required - LLM Provider (at least one)
export OPENAI_API_KEY="sk-..."
# export ANTHROPIC_API_KEY="sk-ant-..."  # optional

# Optional - Features
export BACKGROUND_JOBS_ENABLED="true"
export CORS_ALLOW_ORIGINS="https://yourdomain.com"
export OTEL_ENABLED="true"
export OTEL_SERVICE_NAME="mini-rag-production"
```

### 2. Database Setup ✅
```bash
# Install pgvector extension
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run schema
psql $DATABASE_URL < db_schema.sql

# Verify tables
psql $DATABASE_URL -c "\dt"
# Should show: users, organizations, workspaces, api_keys, workspace_quota_settings, etc.
```

### 3. Data Cleanup ✅
```bash
# Ensure no demo data ships
[ ! -f out/chunks.jsonl ] || rm out/chunks.jsonl

# Create empty chunks file (server will populate)
mkdir -p out
touch out/chunks.jsonl

# Verify backups directory exists
mkdir -p backups
```

### 4. Secret Validation ✅
```bash
# Run validation (should NOT have ALLOW_INSECURE_DEFAULTS set)
python3 -c "
import os
from config_utils import ensure_not_placeholder

# This will raise an error if any secrets are placeholders
ensure_not_placeholder(os.getenv('SECRET_KEY'), 'SECRET_KEY')
ensure_not_placeholder(os.getenv('STRIPE_API_KEY'), 'STRIPE_API_KEY')
print('✅ All secrets validated')
"
```

### 5. Docker Build ✅
```bash
# Build image
docker build -t mini-rag:latest .

# Test locally with real secrets
docker-compose up --build

# Verify health
curl http://localhost:8000/health
# Should return: {"status":"ok","database":"connected","index_loaded":true}
```

## Post-Deployment Verification

### 1. Health Checks ✅
```bash
# Application health
curl https://yourdomain.com/health

# Metrics endpoint
curl https://yourdomain.com/metrics | grep "ask_requests_total"

# Database connectivity
curl https://yourdomain.com/health | jq '.database'
# Should return: "connected"
```

### 2. Authentication Flow ✅
```bash
# OAuth callback URL registered in Google Console
https://yourdomain.com/auth/callback

# Test OAuth redirect
curl -I https://yourdomain.com/auth/google
# Should 302 to accounts.google.com
```

### 3. Stripe Webhook ✅
```bash
# Configure webhook in Stripe dashboard
https://yourdomain.com/api/v1/billing/webhook

# Test with Stripe CLI
stripe listen --forward-to https://yourdomain.com/api/v1/billing/webhook
stripe trigger checkout.session.completed
```

### 4. API Key Generation ✅
```bash
# Create first admin user via OAuth login
# Then generate API key for integrations

# SSH into production
python scripts/manage_api_keys.py create \
  --user <admin-user-uuid> \
  --scope read --scope write --scope admin

# Copy the printed key (only shown once!)
```

### 5. Workspace & Quota Setup ✅
```sql
-- Connect to production DB
psql $DATABASE_URL

-- Verify default org/workspace created
SELECT id, name, plan FROM organizations;
SELECT id, name, organization_id FROM workspaces;

-- Adjust quotas for production tier (example)
INSERT INTO workspace_quota_settings (workspace_id, chunk_limit, request_limit_per_day, request_limit_per_minute)
VALUES ('<workspace-uuid>', 100000, 10000, 100)
ON CONFLICT (workspace_id) DO UPDATE
SET chunk_limit = EXCLUDED.chunk_limit,
    request_limit_per_day = EXCLUDED.request_limit_per_day,
    request_limit_per_minute = EXCLUDED.request_limit_per_minute;
```

### 6. Observability Setup ✅
```bash
# Prometheus scrape config
- job_name: 'mini-rag'
  static_configs:
    - targets: ['yourdomain.com:8000']
  metrics_path: '/metrics'

# Import Grafana dashboard
# Upload: docs/infra/metrics_alerts/mini-rag-dashboard.json

# Load Prometheus alerts
# Copy: docs/infra/metrics_alerts/mini-rag-alerts.yml to /etc/prometheus/rules/

# Reload Prometheus
curl -X POST http://prometheus:9090/-/reload
```

### 7. Smoke Test ✅
```bash
# Create test workspace/user via UI
# Upload a sample document
# Query: "What is this document about?"
# Verify answer + chunks returned

# Check logs for errors
docker logs mini-rag-app | grep ERROR

# Check Prometheus metrics
curl https://yourdomain.com/metrics | grep "ask_request_latency_seconds"
```

## Security Hardening

### SSL/TLS ✅
- [ ] HTTPS enforced (no HTTP traffic allowed)
- [ ] Valid SSL certificate (Let's Encrypt or commercial)
- [ ] HSTS headers enabled (already in middleware)
- [ ] Secure cookies (HttpOnly, Secure flags set)

### Network ✅
- [ ] Database not publicly accessible (private network only)
- [ ] Redis/cache layer on private network
- [ ] Rate limiting enabled (SlowAPI configured)
- [ ] CORS restricted to known domains

### Secrets ✅
- [ ] No secrets in git history
- [ ] Secrets injected via environment (not files)
- [ ] Secret rotation plan documented
- [ ] Stripe webhook secret verified on every request

### Access Control ✅
- [ ] OAuth redirect URIs whitelisted in Google Console
- [ ] First user becomes admin (subsequent users are readers)
- [ ] Admin endpoints require admin scope
- [ ] API keys scoped per workspace

## Rollback Plan

### Database Rollback
```bash
# Backup before migration
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d-%H%M%S).sql

# Restore if needed
psql $DATABASE_URL < backup-20251123-120000.sql
```

### Application Rollback
```bash
# Tag before deploy
git tag production-$(date +%Y%m%d-%H%M%S)
git push --tags

# Rollback
git checkout production-20251123-120000
docker build -t mini-rag:rollback .
docker-compose up -d
```

### Chunk Data Rollback
```bash
# Backups are automatic on every mutation
ls -lh backups/

# Restore from latest
cp backups/latest.jsonl out/chunks.jsonl

# Or use CLI
python raglite.py restore-backup --chunks out/chunks.jsonl
```

## Monitoring Alerts

### Critical (Page Immediately)
- [ ] Health check fails for >2 minutes
- [ ] Database connection lost
- [ ] Ask request error rate >5% for 5 minutes
- [ ] P95 latency >5s for 5 minutes

### Warning (Slack/Email)
- [ ] Workspace quota >90% for any tenant
- [ ] Background job failures present
- [ ] External API errors (Stripe/OpenAI) >10/min
- [ ] Disk space <20% remaining

## Support Runbook

### User Can't Log In
1. Check Google OAuth credentials are set
2. Verify redirect URI matches dashboard: `https://yourdomain.com/auth/callback`
3. Check logs: `docker logs mini-rag-app | grep "oauth"`

### Ingestion Blocked
1. Check billing status: `psql $DATABASE_URL -c "SELECT name, billing_status FROM organizations;"`
2. Check quotas: `curl https://yourdomain.com/metrics | grep workspace_quota_ratio`
3. Review logs: `grep "billing.blocked" logs/rag.log`

### Slow Queries
1. Check Prometheus: P95 latency dashboard
2. Profile query: Add `?debug=1` param to capture timings
3. Review chunk count: Large indexes need optimization

### Database Migration Failed
1. Restore from backup: `psql $DATABASE_URL < backup.sql`
2. Check schema version: `\d` in psql
3. Re-run migration after fix

---

**Last Updated:** 2025-11-23  
**Maintained By:** Platform Team  
**Next Review:** Before each production deploy

