# Security Audit Checklist

Comprehensive security review checklist for Mini-RAG deployments.

---

## 🔐 Authentication & Authorization

### Google OAuth Configuration
- [ ] Client ID and secret stored in environment variables (not code)
- [ ] Redirect URI whitelisted in Google Cloud Console
- [ ] Redirect URI uses HTTPS in production
- [ ] OAuth state parameter validated (CSRF protection)
- [ ] Token expiry set appropriately (7 days max recommended)

### JWT Implementation
- [ ] Secret key is strong (32+ bytes, random)
- [ ] SECRET_KEY is unique per environment (dev/staging/prod)
- [ ] Tokens include expiry (`exp` claim)
- [ ] Tokens are HttpOnly cookies (not localStorage)
- [ ] Secure flag set on cookies in production
- [ ] SameSite=Lax or Strict to prevent CSRF

### API Keys
- [ ] Keys are hashed (SHA-256) before storage
- [ ] Keys are generated with sufficient entropy (32+ chars)
- [ ] Keys are prefixed (`mrag_`) for easy identification
- [ ] Revoked keys are marked (not deleted) for audit trail
- [ ] Last-used timestamp tracked for monitoring
- [ ] Scopes enforced on every request
- [ ] Keys can be rotated without downtime

###Authorization
- [ ] All sensitive endpoints require authentication
- [ ] RBAC enforced (admin/editor/reader roles)
- [ ] Workspace-scoped data isolation working
- [ ] API key scopes checked before operations
- [ ] Admin endpoints return 403 for non-admins
- [ ] Users cannot access other workspaces' data

**Test:**
```bash
# Should fail without auth
curl http://localhost:8000/api/v1/ask  # 401

# Should fail with read-only key on write endpoint
curl -H "X-API-Key: read_only_key" -X POST http://localhost:8000/api/ingest_files  # 403

# Should fail to access other workspace data
curl -H "X-API-Key: workspace_a_key" http://localhost:8000/api/v1/sources?workspace_id=workspace_b  # 403
```

---

## 🌐 Network Security

### HTTPS/TLS
- [ ] Valid SSL certificate (not self-signed in prod)
- [ ] Certificate auto-renewal configured (Let's Encrypt)
- [ ] HTTP redirects to HTTPS
- [ ] HSTS header enabled (`Strict-Transport-Security`)
- [ ] TLS 1.2+ only (no SSL, TLS 1.0/1.1)
- [ ] Strong cipher suites configured

### CORS
- [ ] `CORS_ALLOW_ORIGINS` set to specific domains (not `*` in prod)
- [ ] Credentials allowed only for trusted origins
- [ ] Preflight requests handled correctly

### Security Headers
- [ ] `X-Content-Type-Options: nosniff`
- [ ] `X-Frame-Options: DENY` or `SAMEORIGIN`
- [ ] `Content-Security-Policy` configured
- [ ] `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] `X-XSS-Protection: 1; mode=block`

**Test:**
```bash
curl -I https://yourdomain.com | grep -E "(Strict-Transport|X-Frame|Content-Security)"
```

---

## 🛡️ Input Validation

### File Uploads
- [ ] File type whitelist enforced (`.pdf`, `.docx`, etc.)
- [ ] File size limits enforced (100MB max)
- [ ] Filenames sanitized (no path traversal)
- [ ] Files stored with random UUIDs (not user-supplied names)
- [ ] MIME type validation (not just extension)
- [ ] Malware scanning considered (ClamAV, cloud service)

### Query Parameters
- [ ] Query length limited (5000 chars max)
- [ ] `k` parameter validated (1-100 range)
- [ ] Workspace ID validated as UUID
- [ ] No SQL injection possible (parameterized queries)
- [ ] No NoSQL injection (if using MongoDB/Redis for queries)

### API Payloads
- [ ] All endpoints use Pydantic models
- [ ] JSON payloads validated
- [ ] Nested objects have depth limits
- [ ] Array lengths limited
- [ ] String lengths limited

**Attack Vector Tests:**
```bash
# Path traversal attempt
curl -F "files=@../../etc/passwd" http://localhost:8000/api/ingest_files

# SQL injection attempt
curl "http://localhost:8000/api/v1/sources?workspace_id=' OR '1'='1"

# Oversized payload
curl -X POST http://localhost:8000/api/v1/ask -d "query=$(python -c 'print(\"a\"*10000)')"
```

---

## 💾 Data Protection

### Secrets Management
- [ ] No secrets in code or git history
- [ ] Environment variables used for all secrets
- [ ] `.env` file gitignored
- [ ] Production secrets rotated regularly (90 days)
- [ ] Secrets stored in vault/KMS (not files)
- [ ] Database credentials unique per environment
- [ ] Stripe keys are restricted (not full-access)
- [ ] OpenAI/Anthropic keys have usage limits

### Database Security
- [ ] Database not publicly accessible
- [ ] Connection uses TLS/SSL
- [ ] Strong database password (16+ chars)
- [ ] Least-privilege user accounts
- [ ] Regular backups (automated)
- [ ] Backup encryption enabled
- [ ] Point-in-time recovery configured

### Data at Rest
- [ ] Database encryption enabled
- [ ] Chunk file backups secured (S3 encryption, etc.)
- [ ] Logs don't contain sensitive data (PII, secrets)
- [ ] Redis persistence secured (if enabled)

### Data in Transit
- [ ] All external API calls use HTTPS
- [ ] Internal service-to-service uses TLS (if applicable)
- [ ] Database connections encrypted

**Test:**
```bash
# Check database TLS
psql "$DATABASE_URL&sslmode=require" -c "SELECT 1"

# Verify no secrets in logs
grep -r "sk_live" logs/  # Should be empty
grep -r "password" logs/  # Should be empty
```

---

## 🚦 Rate Limiting & DoS Protection

### Application Layer
- [ ] SlowAPI configured (30 req/min for /ask)
- [ ] Upload rate limits (10/hour)
- [ ] Per-IP rate limiting
- [ ] Per-user rate limiting
- [ ] Workspace quotas enforced
- [ ] Request timeouts configured (30s for /ask)

### Infrastructure Layer
- [ ] WAF configured (Cloudflare, AWS WAF)
- [ ] DDoS protection enabled
- [ ] Connection limits set
- [ ] Slow attack protection (slow POST)

### Resource Limits
- [ ] Max file upload size (100MB)
- [ ] Max request body size
- [ ] Max concurrent connections
- [ ] Memory limits per process
- [ ] CPU limits per container/pod

**Test:**
```bash
# Rate limit test
for i in {1..35}; do
  curl -X POST http://localhost:8000/api/v1/ask -F "query=test" &
done
# Should see 429 errors after 30 requests
```

---

## 🔍 Logging & Monitoring

### Audit Logging
- [ ] All authentication events logged
- [ ] All authorization failures logged
- [ ] Admin operations logged
- [ ] Billing events logged
- [ ] API key creation/revocation logged
- [ ] Logs include: timestamp, user_id, workspace_id, action, outcome
- [ ] Logs stored securely (append-only, no tampering)
- [ ] Log retention policy defined (90 days minimum)

### Security Monitoring
- [ ] Failed login attempts monitored
- [ ] Unusual access patterns detected
- [ ] Quota breaches alerted
- [ ] Billing issues alerted
- [ ] High error rates alerted
- [ ] Slow queries logged
- [ ] External API failures tracked

### Sensitive Data Handling
- [ ] No passwords in logs
- [ ] No API keys in logs
- [ ] No PII in logs (unless necessary)
- [ ] Credit card numbers never stored
- [ ] Logs sanitized before export

**Test:**
```bash
# Check for leaked secrets
grep -r "sk_" logs/ | grep -v "sk_test"  # Should be empty
grep -r "password" logs/  # Should be empty
```

---

## 🧪 Dependency Security

### Package Management
- [ ] Dependencies pinned to specific versions
- [ ] No known vulnerabilities (run `pip-audit`)
- [ ] Transitive dependencies reviewed
- [ ] Unused dependencies removed
- [ ] Private package registry (if applicable)

### CI/CD Security
- [ ] Dependency scanning in pipeline
- [ ] SAST (static analysis) enabled
- [ ] Container image scanning
- [ ] Secrets scanning (detect leaked keys)
- [ ] Branch protection enabled
- [ ] Code review required before merge
- [ ] Signed commits required (optional)

**Test:**
```bash
# Check for vulnerabilities
pip install pip-audit
pip-audit

# Check for outdated packages
pip list --outdated
```

---

## 🔧 Infrastructure Security

### Docker/Container
- [ ] Non-root user in Dockerfile
- [ ] Minimal base image (Alpine, distroless)
- [ ] No secrets in image layers
- [ ] Image signing enabled
- [ ] Registry security scanning
- [ ] Resource limits set (CPU, memory)
- [ ] Read-only root filesystem (where possible)

### Kubernetes (if applicable)
- [ ] NetworkPolicies configured
- [ ] PodSecurityPolicies enforced
- [ ] RBAC for service accounts
- [ ] Secrets stored in Secrets API (not ConfigMaps)
- [ ] Ingress TLS termination
- [ ] Pod-to-pod encryption (service mesh)

### Cloud Services
- [ ] IAM roles with least privilege
- [ ] S3 buckets not public
- [ ] Security groups restrict access
- [ ] Encryption at rest enabled
- [ ] VPC isolated from internet (private subnets)
- [ ] Bastion host for admin access only

**Test:**
```bash
# Check Docker security
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image mini-rag:latest
```

---

## 🧩 Third-Party Integrations

### Stripe
- [ ] Webhook signature validation enabled
- [ ] Test keys used in dev/staging
- [ ] API keys are restricted (not full-access)
- [ ] Idempotency keys used for mutations
- [ ] Customer data not over-collected
- [ ] PCI compliance considered (if storing payment info)

### OpenAI/Anthropic
- [ ] API keys have usage limits
- [ ] Rate limiting on client side
- [ ] Retry logic with exponential backoff
- [ ] Embeddings cached (reduce costs)
- [ ] User input sanitized before sending
- [ ] No PII sent in prompts (if avoidable)

### OAuth (Google)
- [ ] Client secret rotated periodically
- [ ] Scopes minimal (only email, profile)
- [ ] Tokens validated on every use
- [ ] Refresh token flow secure
- [ ] Account takeover protection (rate limits)

---

## 📋 Compliance

### GDPR (if applicable)
- [ ] Privacy policy published
- [ ] User consent obtained
- [ ] Data retention policy defined
- [ ] Right to be forgotten implemented (delete user data)
- [ ] Data export available (download my data)
- [ ] Data processors documented (Stripe, OpenAI, etc.)
- [ ] DPA signed with processors
- [ ] Data breach notification process defined

### SOC 2 (if pursuing)
- [ ] Access controls documented
- [ ] Change management process
- [ ] Incident response plan
- [ ] Vendor risk management
- [ ] Security awareness training
- [ ] Regular security audits
- [ ] Penetration testing annual

---

## ✅ Pre-Deployment Checklist

### Critical (Must Fix)
- [ ] All placeholder secrets replaced
- [ ] `ALLOW_INSECURE_DEFAULTS` not set (or =false)
- [ ] HTTPS enabled
- [ ] Authentication working
- [ ] Database encrypted
- [ ] Backups configured
- [ ] Rate limiting enabled

### High Priority
- [ ] Security headers configured
- [ ] Dependency scan passes
- [ ] Secrets in vault/KMS
- [ ] Monitoring/alerting active
- [ ] Incident response plan documented

### Medium Priority
- [ ] Audit logging complete
- [ ] Penetration testing done
- [ ] Privacy policy reviewed
- [ ] Security training completed

---

## 🛠️ Tools & Resources

### Automated Scanning
```bash
# Dependency vulnerabilities
pip install pip-audit
pip-audit

# Container scanning
trivy image mini-rag:latest

# Secret scanning
trufflehog git file://. --only-verified

# SAST
bandit -r .

# License compliance
pip-licenses --format=markdown
```

### Manual Testing
- OWASP ZAP (web app scanner)
- Burp Suite (intercepting proxy)
- SQLMap (SQL injection testing)
- Nikto (web server scanner)

### Compliance Tools
- Vanta (SOC 2 automation)
- Drata (compliance automation)
- OneTrust (GDPR compliance)

---

**Review Schedule:**
- **Weekly:** Dependency scan, log review
- **Monthly:** Access review, incident response drill
- **Quarterly:** Penetration testing, security training
- **Annually:** Full security audit, compliance review

**Last Audit:** [Date]  
**Next Audit:** [Date]  
**Auditor:** [Name/Team]

