# Quick Setup on Second Machine (If Script Missing)

If `setup_new_machine.sh` isn't available, follow these manual steps:

## Manual Setup Steps

### 1. Install Dependencies

**Python:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Node.js:**
```bash
cd frontend-react
npm install
npm run build
cd ..
```

### 2. Create .env File

```bash
# Copy template
cp PRODUCTION_ENV_TEMPLATE .env

# Or create basic .env
cat > .env << EOF
LOCAL_MODE=true
ALLOW_INSECURE_DEFAULTS=true
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
OPENAI_API_KEY=your-openai-key-here
DATABASE_URL=postgresql://postgres:postgres@your-db-host:5432/rag_brain
EOF
```

### 3. Configure DATABASE_URL

Edit `.env` and set your shared database URL:
```bash
nano .env
```

### 4. Initialize Database (if needed)

```bash
psql $DATABASE_URL < db_schema.sql
```

### 5. Start Server

```bash
./START_LOCAL.sh
```

Or:
```bash
source venv/bin/activate
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

---

## Alternative: Get Scripts from First Machine

**Option A: Copy files directly**
- Copy `setup_new_machine.sh` from Machine A to Machine B
- Make executable: `chmod +x setup_new_machine.sh`

**Option B: Commit to Git (recommended)**
On Machine A:
```bash
git add setup_new_machine.sh SETUP_NEW_MACHINE.md SHARED_DATABASE_SETUP.md START_ON_SECOND_MACHINE.md scripts/setup_shared_db.sh
git commit -m "Add setup scripts for multi-machine deployment"
git push
```

On Machine B:
```bash
git pull
./setup_new_machine.sh
```


