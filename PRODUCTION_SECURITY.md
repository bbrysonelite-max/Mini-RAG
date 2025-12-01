# Production Security Configuration

## LOCAL_MODE Disable for Production

**IMPORTANT:** `LOCAL_MODE` bypasses authentication and should NEVER be enabled in production.

### Current Status
- `LOCAL_MODE` is controlled by environment variable
- Default: `false` (disabled)
- When enabled: Allows unauthenticated access (development only)

### Production Setup

1. **Verify LOCAL_MODE is disabled:**
   ```bash
   # On Railway, ensure LOCAL_MODE is NOT set or set to "false"
   ```

2. **Set in Railway Environment Variables:**
   - `LOCAL_MODE=false` (or don't set it - defaults to false)
   - `ALLOW_INSECURE_DEFAULTS=false` (for production)

3. **Verify Authentication is Required:**
   - All endpoints should return 401 without authentication
   - Login form should be shown to unauthenticated users

### Security Checklist

- [ ] `LOCAL_MODE` is not set or set to `false` in production
- [ ] `ALLOW_INSECURE_DEFAULTS` is `false` in production
- [ ] `CORS_ALLOW_ORIGINS` is set to specific domains (not `*`)
- [ ] `SECRET_KEY` is set to a strong random value (not default)
- [ ] HTTPS is enabled (Railway handles this automatically)
- [ ] Rate limiting is active on login endpoint (5/minute)
- [ ] Password requirements enforced (min 8 characters)

## CORS Configuration

### Production Setup
Set `CORS_ALLOW_ORIGINS` to your specific domains:
```
CORS_ALLOW_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Development Setup
For local development, you can use:
```
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Rate Limiting

- **Login endpoint:** 5 attempts per minute
- **Ask endpoint:** 30 requests per minute
- **Ingest endpoints:** 10 requests per hour

## Password Security

- Minimum length: 8 characters
- Stored as bcrypt hash (12 rounds)
- Never logged or exposed in error messages

## Account Lockout

Currently not implemented. Consider adding:
- Lock account after 5 failed login attempts
- Unlock after 15 minutes or admin intervention

