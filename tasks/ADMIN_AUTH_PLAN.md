# Admin Authentication & Security Features Plan

## Goal
Add administrator username/password authentication to the database, enabling secure admin login without requiring Google OAuth.

## Current State
- ✅ Database has `users` table with email, name, role
- ✅ Google OAuth authentication exists
- ✅ First user automatically gets admin role
- ❌ No password field in users table
- ❌ No username/password login endpoint
- ⚠️ Currently using `LOCAL_MODE=true` (bypasses auth)

## What Needs to Be Done

### 1. Database Schema Changes ✅ Added to TODO
**Add password support to users table:**
- Add `username` field (unique)
- Add `password_hash` field (bcrypt hashed)
- Add `auth_method` field ('oauth' or 'password')
- Keep existing OAuth users working

**Migration:**
```sql
ALTER TABLE users 
  ADD COLUMN IF NOT EXISTS username VARCHAR(255) UNIQUE,
  ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255),
  ADD COLUMN IF NOT EXISTS auth_method VARCHAR(50) DEFAULT 'oauth';
```

### 2. Create Admin User Script ✅ Added to TODO
**Script to create admin user with username/password:**
- `scripts/create_admin_user.py`
- Prompts for username and password
- Hashes password with bcrypt
- Creates user with role='admin'
- Sets auth_method='password'

**Usage:**
```bash
python scripts/create_admin_user.py
# Enter username: admin
# Enter password: [secure password]
# Admin user created!
```

### 3. Admin Login Endpoint ✅ Added to TODO
**New endpoint:** `POST /auth/login`
- Accepts username and password
- Validates against database
- Returns JWT token (same format as OAuth)
- Sets httponly cookie

**Request:**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "jwt-token",
  "user": {
    "id": "uuid",
    "username": "admin",
    "email": null,
    "role": "admin"
  }
}
```

### 4. Update Authentication System ✅ Added to TODO
**Modify `auth.py` and `server.py`:**
- Support both OAuth and password authentication
- Check `auth_method` field
- Password users can login via `/auth/login`
- OAuth users continue using Google login
- Both get same JWT tokens

### 5. Security Features ✅ Added to TODO
**Enable proper authentication:**
- Set `LOCAL_MODE=false` in production
- Require authentication for all endpoints
- Add rate limiting on login endpoint
- Add password strength requirements
- Add account lockout after failed attempts

### 6. Admin User Management ✅ Added to TODO
**Admin panel features:**
- List all users
- Create new admin users
- Change user roles
- Reset passwords
- View user activity

## Implementation Steps

### Step 1: Database Migration
1. Add columns to users table
2. Create migration script
3. Run migration on production database

### Step 2: Create Admin User
1. Create `scripts/create_admin_user.py`
2. Run script to create your admin account
3. Verify user exists in database

### Step 3: Login Endpoint
1. Add `POST /auth/login` endpoint
2. Implement password verification
3. Return JWT token
4. Test login flow

### Step 4: Update Auth System
1. Modify `_resolve_auth_context()` to support both methods
2. Update JWT creation for password users
3. Ensure both auth methods work

### Step 5: Security Hardening
1. Disable LOCAL_MODE in production
2. Add rate limiting
3. Add password requirements
4. Add failed login tracking

### Step 6: Admin UI
1. Add login form to frontend
2. Add admin user management panel
3. Add user list/management features

## Files to Create/Modify

### New Files:
- `scripts/create_admin_user.py` - Admin user creation script
- `scripts/migrate_add_passwords.py` - Database migration script
- `frontend-react/src/components/LoginForm.tsx` - Username/password login form
- `frontend-react/src/components/AdminPanel.tsx` - Admin user management

### Files to Modify:
- `db_schema.sql` - Add username, password_hash, auth_method columns
- `server.py` - Add `/auth/login` endpoint
- `auth.py` - Support password authentication
- `user_service.py` - Add password hashing/verification methods
- `frontend-react/src/App.tsx` - Add login form

## Security Considerations

1. **Password Hashing:** Use bcrypt with salt rounds (12+)
2. **Rate Limiting:** Limit login attempts (5 per 15 minutes)
3. **Password Requirements:** Min 12 characters, complexity rules
4. **Account Lockout:** Lock after 5 failed attempts for 30 minutes
5. **HTTPS Only:** Require HTTPS in production
6. **Session Management:** JWT tokens expire after 7 days
7. **Audit Logging:** Log all admin actions

## Testing Plan

1. ✅ Create admin user via script
2. ✅ Test login with username/password
3. ✅ Verify JWT token is created
4. ✅ Test admin endpoints work
5. ✅ Test OAuth still works
6. ✅ Test rate limiting
7. ✅ Test password requirements
8. ✅ Test account lockout

## Success Criteria

- [ ] Admin user exists in database with username/password
- [ ] Can login via `/auth/login` endpoint
- [ ] JWT token is created and works
- [ ] Admin endpoints are accessible
- [ ] OAuth login still works
- [ ] LOCAL_MODE can be disabled
- [ ] Security features are enabled

## Priority

**HIGH** - This is critical for production security and admin access.



