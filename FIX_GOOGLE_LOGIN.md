# 🔧 FIX: Google Login Not Working

## **The Problem:**
Google OAuth redirect URI is not registered in your Google Cloud Console.

## **The Fix (5 minutes):**

### **Step 1: Go to Google Cloud Console**
```
https://console.cloud.google.com/apis/credentials
```

### **Step 2: Find Your OAuth Client**
- Look for Client ID: `1059104880024-diifu571kdg5bpsneq34tdgck3npmi5s`
- Click on it

### **Step 3: Add Redirect URI**

Under **"Authorized redirect URIs"**, add:
```
http://localhost:8000/auth/callback
```

**Important:** Use `/auth/callback` NOT `/auth/google/callback`

Click **SAVE**

### **Step 4: Test Again**
```bash
# No need to restart server
# Just click "Sign in with Google" again
# Should work now!
```

---

## **Alternative: Temporary Workaround (Skip OAuth)**

If you want to test WITHOUT fixing Google OAuth right now:

### **Option A: Use the System Without Login**
The UI works without authentication for read-only features:
- ✅ View sources
- ✅ Browse documents (if any exist)
- ❌ Can't upload (needs auth)
- ❌ Can't ask questions (needs auth)

### **Option B: Generate an API Key Manually**
```bash
cd /Users/brentbryson/Desktop/mini-rag

# Create a test user manually
./venv/bin/python3 << 'PY'
import uuid
import json

# Create fake user for testing
user_id = str(uuid.uuid4())
print(f"Test User ID: {user_id}")

# Save to file
with open("/tmp/test_user.json", "w") as f:
    json.dump({"user_id": user_id, "email": "test@example.com"}, f)
PY

# Then use the test endpoints that don't require full OAuth
```

---

## **Most Likely Issue:**

Your Google Console redirect URI is probably set to something like:
- ❌ `http://localhost:8000/auth/google/callback` (WRONG - extra `/google`)
- ❌ `https://localhost:8000/auth/callback` (WRONG - uses `https`)
- ❌ `http://localhost:3000/auth/callback` (WRONG - wrong port)

**Should be:**
- ✅ `http://localhost:8000/auth/callback` (CORRECT)

---

## 🔍 **How to Verify It's Fixed:**

1. Update redirect URI in Google Console
2. Wait 30 seconds (Google needs to sync)
3. Click "Sign in with Google" again
4. Should redirect to Google
5. After approving, should redirect back to app
6. You'll be signed in!

---

## **Check Server Logs for More Details:**
```bash
tail -f /tmp/server.log
# Then click "Sign in with Google"
# Watch for errors
```

---

## ✅ **Quick Fix Checklist:**

- [ ] Go to: https://console.cloud.google.com/apis/credentials
- [ ] Find your OAuth client
- [ ] Add redirect URI: `http://localhost:8000/auth/callback`
- [ ] Save
- [ ] Try login again

**ETA: 3 minutes** ⏱️

---

**Let me know when you've added the redirect URI and I'll help you test!**



