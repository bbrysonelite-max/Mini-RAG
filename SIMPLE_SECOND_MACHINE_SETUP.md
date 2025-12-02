# Simple Setup on Second Machine

## Step 1: Set up Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 2: Build frontend

```bash
cd frontend-react
npm install
npm run build
cd ..
```

## Step 3: Configure .env

```bash
cp PRODUCTION_ENV_TEMPLATE .env
nano .env
```

Set these values:
- `LOCAL_MODE=true`
- `ALLOW_INSECURE_DEFAULTS=true`
- `DATABASE_URL=postgresql://postgres:postgres@<machine-a-ip>:5432/rag_brain`
- `OPENAI_API_KEY=sk-your-key`
- `SECRET_KEY=` (generate: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`)

Save: Ctrl+X, Y, Enter

## Step 4: Initialize database

```bash
source .env
psql $DATABASE_URL < db_schema.sql
```

## Step 5: Start server

```bash
source venv/bin/activate
./START_LOCAL.sh
```

Open: http://localhost:8000/app
