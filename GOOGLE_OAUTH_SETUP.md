# Google OAuth Setup Guide

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter project name: `Mini-RAG` (or your preferred name)
5. Click "Create"
6. Wait for project creation, then select it

## Step 2: Enable Google+ API

1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google+ API" or "People API"
3. Click on it and click "Enable"
4. Also enable "Google Identity Services API" if available

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen first:
   - User Type: External (unless you have Google Workspace)
   - App name: Mini-RAG
   - User support email: (your email)
   - Developer contact: (your email)
   - Click "Save and Continue"
   - Scopes: Add `email` and `profile`
   - Click "Save and Continue"
   - Test users: Add your email (for testing)
   - Click "Save and Continue"

4. Back to creating OAuth client:
   - Application type: **Web application**
   - Name: `Mini-RAG Web Client`
   - Authorized JavaScript origins:
     - `http://localhost:8000`
     - `http://127.0.0.1:8000`
   - Authorized redirect URIs:
     - `http://localhost:8000/auth/google/callback`
     - `http://127.0.0.1:8000/auth/google/callback`
   - Click "Create"

5. **IMPORTANT:** Copy the Client ID and Client Secret immediately
   - You'll need these in the next step
   - The secret won't be shown again!

## Step 4: Store Credentials Securely

Create a `.env` file in your project root with:

```
GOOGLE_CLIENT_ID=your-client-id-here
GOOGLE_CLIENT_SECRET=your-client-secret-here
SECRET_KEY=generate-a-random-secret-key-here
```

**Never commit `.env` to git!** It's already in `.gitignore`

## Step 5: Generate Secret Key

Run this command to generate a secure secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and use it as your `SECRET_KEY` in `.env`

---

## Next Steps

Once you have:
- ✅ Google Cloud project created
- ✅ OAuth credentials (Client ID and Secret)
- ✅ `.env` file created with credentials

Let me know and we'll proceed to Step 2: Install dependencies and implement the OAuth flow.

done 
