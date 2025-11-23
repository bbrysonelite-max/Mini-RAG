# 🚀 FINAL LAUNCH CHECKLIST

**Complete these steps to go live:**

---

## ✅ **PRE-LAUNCH (Do Once)**

### 1. Get Credentials (30 minutes)

#### Google OAuth:
```bash
1. Visit: https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID
3. Add redirect URI: https://yourdomain.com/auth/callback
4. Copy Client ID and Secret
```

#### OpenAI API:
```bash
1. Visit: https://platform.openai.com/api-keys
2. Create new secret key
3. Copy key (starts with sk-)
```

#### Stripe (Optional):
```bash
1. Visit: https://dashboard.stripe.com/test/apikeys
2. Copy test API key
3. Create product + price, copy price ID
4. For webhooks: stripe listen --forward-to localhost:8000/api/v1/billing/webhook
```

### 2. Create .env File
```bash
# Copy template
cp PRODUCTION_ENV_TEMPLATE .env

# Generate SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Edit .env with real values
nano .env
```

### 3. Verify Docker Setup
```bash
# Check Docker is running
docker --version
docker-compose --version

# Should see:
# Docker version 24.x.x
# Docker Compose version v2.x.x
```

---

## 🚀 **LAUNCH (Execute Now)**

### Step 1: Start Services (5 min)
```bash
cd /Users/brentbryson/Desktop/mini-rag

# Start database first
docker-compose up -d db

# Wait for DB to be ready
sleep 10

# Initialize database schema
docker exec -i mini-rag_db_1 psql -U postgres -d rag_brain < db_schema.sql

# Start app
docker-compose up -d app

# Check logs
docker-compose logs -f app
```

**✅ Checkpoint:** Logs show "Application startup complete"

### Step 2: Health Check (2 min)
```bash
# Wait for startup
sleep 30

# Check health
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","database":"connected","index_loaded":true}
```

**✅ Checkpoint:** Health check returns 200

### Step 3: Smoke Tests (5 min)
```bash
# Run automated smoke tests
./scripts/smoke_test.sh

# Should see:
# ✅ All critical tests passed!
```

**✅ Checkpoint:** All smoke tests pass

### Step 4: Manual Functional Test (10 min)
```bash
# 1. Open browser: http://localhost:8000/app
# 2. Click "Sign in with Google"
# 3. Complete OAuth flow
# 4. Click "Ingest" tab
# 5. Upload a test .txt file with some content
# 6. Click "Ask" tab
# 7. Type question: "What is this document about?"
# 8. Click "Ask"
# 9. Verify answer appears
```

**✅ Checkpoint:** Can upload docs and ask questions

### Step 5: Load Test Baseline (5 min)
```bash
# Install locust
pip3 install locust

# Generate API key first (need to be logged in)
# Then export it
export MINI_RAG_API_KEY="your_api_key_here"

# Run 3-minute load test
locust -f scripts/load_test.py \
  --host http://localhost:8000 \
  --headless -u 10 -r 2 --run-time 3m

# Note the results:
# - Total requests
# - Failures
# - P50/P95 latency
# - Requests/sec
```

**✅ Checkpoint:** Load test completes, <5% errors

---

## 🔒 **SECURITY AUDIT (Critical)**

### Quick Security Check (15 min)
```bash
# 1. Verify no placeholder secrets
grep -i "your-" .env  # Should be empty
grep -i "changeme" .env  # Should be empty

# 2. Test authentication required
curl http://localhost:8000/api/v1/ask  
# Should return 401

# 3. Test rate limiting
for i in {1..35}; do 
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8000/api/v1/ask &
done | grep 429 | wc -l
# Should see several 429s

# 4. Check security headers
curl -I http://localhost:8000/health | grep -E "X-Frame|X-Content|Strict-Transport"
# Should see security headers

# 5. Scan dependencies
pip3 install pip-audit
pip-audit --require-hashes requirements.txt || true
# Note any CRITICAL vulnerabilities
```

**✅ Checkpoint:** No critical security issues

---

## 📊 **MONITORING SETUP (Optional but Recommended)**

### Basic Monitoring (20 min)

#### Option A: Grafana Cloud (Free)
```bash
1. Sign up: https://grafana.com/auth/sign-up
2. Add Prometheus data source
3. Import dashboard: docs/infra/metrics_alerts/mini-rag-dashboard.json
4. Set up basic alerts:
   - Service down
   - Error rate >5%
```

#### Option B: Simple Uptime Monitor
```bash
# Use a free service:
1. https://uptimerobot.com (free)
2. Add HTTP monitor: https://yourdomain.com/health
3. Check every 5 minutes
4. Email on failure
```

**✅ Checkpoint:** Health monitoring active

---

## 🌐 **DEPLOY TO PRODUCTION (Choose One)**

### Option A: Heroku (Easiest - 15 min)
```bash
# Install Heroku CLI
brew tap heroku/brew && brew install heroku

# Login
heroku login

# Create app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:essential-0

# Add Redis
heroku addons:create heroku-redis:mini

# Set environment variables
heroku config:set SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
heroku config:set GOOGLE_CLIENT_ID="your-id"
heroku config:set GOOGLE_CLIENT_SECRET="your-secret"
heroku config:set OPENAI_API_KEY="your-key"
heroku config:set REDIS_ENABLED=true
heroku config:set BACKGROUND_JOBS_ENABLED=true

# Deploy
git push heroku main

# Initialize database
heroku run "psql $DATABASE_URL < db_schema.sql"

# Open app
heroku open
```

### Option B: Render (Easy - 15 min)
```bash
1. Go to: https://render.com
2. Click "New +" → "Web Service"
3. Connect GitHub repo
4. Configure:
   - Name: mini-rag
   - Environment: Docker
   - Instance Type: Starter ($7/month)
5. Add PostgreSQL: New → PostgreSQL
6. Add Redis: New → Redis
7. Set environment variables (same as above)
8. Click "Create Web Service"
9. Wait for deployment
10. Visit your-app.onrender.com
```

### Option C: Fly.io (Fast - 10 min)
```bash
# Install flyctl
brew install flyctl

# Login
fly auth login

# Launch
fly launch

# Add PostgreSQL
fly postgres create

# Add Redis
fly redis create

# Set secrets
fly secrets set SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
fly secrets set GOOGLE_CLIENT_ID="your-id"
fly secrets set GOOGLE_CLIENT_SECRET="your-secret"
fly secrets set OPENAI_API_KEY="your-key"

# Deploy
fly deploy

# Open
fly open
```

**✅ Checkpoint:** App accessible at public URL

---

## ✅ **POST-LAUNCH VERIFICATION**

### Final Checks
```bash
# 1. Update BASE_URL and run smoke tests
export BASE_URL=https://yourdomain.com
./scripts/smoke_test.sh

# 2. Manual test on production URL
# - Visit https://yourdomain.com/app
# - Sign in with Google
# - Upload document
# - Ask question
# - Verify works

# 3. Check metrics
curl https://yourdomain.com/metrics | grep ask_requests_total

# 4. Check logs (platform specific)
# Heroku: heroku logs --tail
# Render: View in dashboard
# Fly: fly logs
```

**✅ Checkpoint:** Production fully functional

---

## 🎉 **YOU'RE LIVE!**

### Success Criteria
- [ ] Health endpoint returns 200
- [ ] OAuth login works
- [ ] Can upload documents
- [ ] Can ask questions and get answers
- [ ] No critical errors in logs
- [ ] Monitoring active
- [ ] Smoke tests passing

### Share Your Launch
```markdown
🚀 Just launched Mini-RAG!

A production-ready multi-tenant RAG system with:
✅ Google OAuth authentication
✅ Stripe billing integration  
✅ Redis caching
✅ OpenTelemetry tracing
✅ Comprehensive monitoring
✅ Full API documentation

Built in [X] hours from planning → production.

Live at: https://yourdomain.com
```

---

## 🆘 **IF SOMETHING BREAKS**

### Quick Fixes
```bash
# Service won't start
docker-compose logs app
# Check for missing env vars or DB connection issues

# Database connection failed
docker-compose restart db
docker-compose logs db

# OAuth not working
# Check redirect URI in Google Console matches exactly

# Health check failing
curl -v http://localhost:8000/health
# Check database connection

# High error rate
grep "ERROR" logs/rag.log | tail -50
# Look for specific error messages
```

### Get Help
1. Check `docs/guides/TROUBLESHOOTING.md`
2. Review `docs/SECURITY_AUDIT.md`
3. Check platform-specific docs
4. Review deployment logs

---

## ⏱️ **TOTAL TIME: 2-4 Hours**

- Credentials: 30 min
- Local testing: 30 min
- Security audit: 15 min
- Deploy: 15-30 min
- Verification: 15 min
- Monitoring: 20 min (optional)
- Buffer: 30 min

**You're ready to launch. Execute this checklist NOW.** 🚀

