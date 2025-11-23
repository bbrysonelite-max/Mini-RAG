# 🚀 GO LIVE NOW - 6 Hour Sprint

**Start Time:** [Write current time]  
**Target Completion:** [+6 hours]

---

## ⏱️ HOUR 1: Local Validation (CURRENT)

**Status:** ✅ COMPLETE

- [x] All files verified present
- [x] Python syntax checked
- [x] Docker available
- [x] Scripts executable
- [x] Documentation complete

**Time:** 10 minutes  
**Next:** Hour 2

---

## ⏱️ HOUR 2: Environment Setup (20 min)

### Step 1: Create Production .env (5 min)
```bash
cd /Users/brentbryson/Desktop/mini-rag

# Generate strong secret
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Create .env
cat > .env << EOF
# === REQUIRED ===
SECRET_KEY=$SECRET_KEY
GOOGLE_CLIENT_ID=your-real-client-id
GOOGLE_CLIENT_SECRET=your-real-secret
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_brain

# === STRIPE (or disable) ===
STRIPE_API_KEY=sk_test_your_key
STRIPE_PRICE_ID=price_your_price
STRIPE_WEBHOOK_SECRET=whsec_your_secret
STRIPE_SUCCESS_URL=http://localhost:8000/success
STRIPE_CANCEL_URL=http://localhost:8000/cancel
STRIPE_PORTAL_RETURN_URL=http://localhost:8000/app

# === LLM (at least one) ===
OPENAI_API_KEY=sk-your-key

# === OPTIONAL ===
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
BACKGROUND_JOBS_ENABLED=true
OTEL_ENABLED=false
EOF
```

### Step 2: Start Services (10 min)
```bash
# Start PostgreSQL + Redis
docker-compose up -d db

# Wait for DB
sleep 10

# Load schema
docker exec -i mini-rag-db psql -U postgres -d rag_brain < db_schema.sql

# Start app
docker-compose up -d app

# Check logs
docker-compose logs -f app
```

### Step 3: Verify Health (5 min)
```bash
# Wait for startup
sleep 30

# Check health
curl http://localhost:8000/health

# Should see: {"status":"ok","database":"connected","index_loaded":true}
```

**Checkpoint:** Services running? ✅ → Hour 3

---

## ⏱️ HOUR 3: Smoke Tests & Load Test (30 min)

### Step 1: Smoke Tests (10 min)
```bash
./scripts/smoke_test.sh

# Should see all tests pass
```

### Step 2: Manual Functional Test (10 min)
```bash
# 1. Visit http://localhost:8000/app
# 2. Click "Sign in with Google"
# 3. Complete OAuth flow
# 4. Upload a test document
# 5. Ask a question
# 6. Verify answer returned
```

### Step 3: Load Test (10 min)
```bash
# Install locust
pip3 install locust

# Run load test
locust -f scripts/load_test.py --host http://localhost:8000 --headless \
  -u 10 -r 2 --run-time 3m

# Capture baseline:
# - P50 latency
# - P95 latency
# - Error rate
# - Throughput (req/s)
```

**Checkpoint:** All tests passing? ✅ → Hour 4

---

## ⏱️ HOUR 4: Security Audit (40 min)

### Quick Security Checklist

Run through `docs/SECURITY_AUDIT.md`:

**Critical Items (20 min):**
- [ ] No placeholder secrets in .env
- [ ] SECRET_KEY is strong (32+ bytes)
- [ ] Database password changed from default
- [ ] HTTPS will be enabled in production
- [ ] Authentication working
- [ ] CORS configured properly
- [ ] Rate limiting active

```bash
# Test authentication
curl http://localhost:8000/api/v1/ask  # Should 401

# Test rate limiting
for i in {1..35}; do curl -X POST http://localhost:8000/api/v1/ask & done
# Should see 429 errors

# Check security headers
curl -I http://localhost:8000/health | grep -E "(X-Frame|X-Content)"
```

**Dependency Scan (10 min):**
```bash
pip3 install pip-audit
pip-audit  # Fix any critical vulnerabilities
```

**Log Review (10 min):**
```bash
# Check for leaked secrets
grep -r "sk_live" logs/  # Should be empty
grep -r "password" logs/  # Should be empty
```

**Checkpoint:** Security audit clean? ✅ → Hour 5

---

## ⏱️ HOUR 5: Production Prep (1 hr)

### Step 1: Get Real Credentials (30 min)

**Google OAuth:**
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID
3. Add redirect URI: `https://yourdomain.com/auth/callback`
4. Copy Client ID and Secret
5. Update .env

**Stripe (if using):**
1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy API key (sk_test_*)
3. Create product + price
4. Get webhook secret: `stripe listen --forward-to localhost:8000/api/v1/billing/webhook`
5. Update .env

**OpenAI:**
1. Go to https://platform.openai.com/api-keys
2. Create new key
3. Update .env

### Step 2: Production Database (20 min)

**Option A: Managed (Recommended)**
- Heroku Postgres
- AWS RDS
- Supabase
- Render

**Option B: Self-Hosted**
```bash
# Use docker-compose but with volumes
docker-compose down
docker volume create mini-rag-pgdata
# Edit docker-compose.yml to use named volume
docker-compose up -d
```

### Step 3: Domain & SSL (10 min)

**Quick Deploy Options:**
- Heroku: `git push heroku main`
- Render: Connect GitHub repo
- Fly.io: `fly deploy`
- Railway: Connect GitHub repo

All provide free SSL automatically.

**Checkpoint:** Real credentials + hosting ready? ✅ → Hour 6

---

## ⏱️ HOUR 6: Deploy & Monitor (1.5 hrs)

### Step 1: Deploy (30 min)

**Using Docker (any host):**
```bash
# Build production image
docker build -t mini-rag:v1.0.0 .

# Push to registry
docker tag mini-rag:v1.0.0 your-registry/mini-rag:v1.0.0
docker push your-registry/mini-rag:v1.0.0

# Deploy
# (Depends on your hosting platform)
```

### Step 2: Post-Deploy Smoke Test (15 min)
```bash
# Update smoke test URL
export BASE_URL=https://yourdomain.com

# Run smoke tests
./scripts/smoke_test.sh

# Manual verification
# 1. Visit https://yourdomain.com/app
# 2. Sign in
# 3. Upload document
# 4. Ask question
# 5. Verify works
```

### Step 3: Monitoring Setup (30 min)

**Grafana Cloud (Free tier):**
1. Sign up: https://grafana.com/auth/sign-up/create-user
2. Add Prometheus data source: `https://yourdomain.com/metrics`
3. Import dashboard: `docs/infra/metrics_alerts/mini-rag-dashboard.json`
4. Set up alerts (critical only):
   - Service down
   - Error rate >5%
   - P95 latency >5s

**Checkpoint:** Production live + monitoring? ✅ → DONE

---

## 🎉 YOU'RE LIVE!

### Post-Launch Checklist

- [ ] Health check passing: `https://yourdomain.com/health`
- [ ] Metrics visible: `https://yourdomain.com/metrics`
- [ ] Authentication working
- [ ] Can upload documents
- [ ] Can ask questions
- [ ] Monitoring dashboard showing data
- [ ] Alerts configured

### Share Your Success

```markdown
🚀 Mini-RAG is LIVE!

- Multi-tenant RAG system
- OAuth + API key auth
- Stripe billing integration
- Redis caching
- Full observability
- Production ready

Built in 6 hours from last-mile → launch.

Try it: https://yourdomain.com
Docs: https://github.com/you/mini-rag
```

---

## 🆘 If Something Breaks

1. **Check logs:**
   ```bash
   docker-compose logs -f app
   grep "ERROR" logs/rag.log
   ```

2. **Run troubleshooting:**
   ```bash
   # See docs/guides/TROUBLESHOOTING.md
   ```

3. **Rollback:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Get help:**
   - Check `docs/guides/TROUBLESHOOTING.md`
   - Review `docs/SECURITY_AUDIT.md`
   - Check deployment logs

---

## ⏰ Timeline Summary

| Hour | Task | Duration | Status |
|------|------|----------|--------|
| 1 | Local validation | 10 min | ✅ |
| 2 | Environment setup | 20 min | ⏳ |
| 3 | Smoke + load tests | 30 min | ⏳ |
| 4 | Security audit | 40 min | ⏳ |
| 5 | Production prep | 1 hr | ⏳ |
| 6 | Deploy + monitor | 1.5 hr | ⏳ |

**Total:** ~4 hours of actual work  
**Buffer:** 2 hours for issues  
**Result:** PRODUCTION LAUNCH 🚀

---

**NOW GO EXECUTE. NO MORE PLANNING.**

Update this file as you complete each hour.

