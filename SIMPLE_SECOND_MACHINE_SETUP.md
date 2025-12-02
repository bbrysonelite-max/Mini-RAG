# Simple Setup on Second Machine

Follow these steps in order. Do not skip any step.

## Step 1: Make sure you're in the right directory

```bash
cd mini-rag
pwd
```

You should see a path ending in `/mini-rag`. If not, navigate to where you copied/cloned the project.

## Step 2: Create Python virtual environment

```bash
python3 -m venv venv
```

Wait for it to finish.

## Step 3: Activate the virtual environment

```bash
source venv/bin/activate
```

You should see `(venv)` at the start of your prompt.

## Step 4: Install Python packages

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will take a few minutes. Wait for it to finish.

## Step 5: Build the frontend

```bash
cd frontend-react
npm install
npm run build
cd ..
```

This will take a few minutes. Wait for it to finish.

## Step 6: Create .env file

```bash
cp PRODUCTION_ENV_TEMPLATE .env
```

## Step 7: Edit .env file

```bash
nano .env
```

In nano, find these lines and change them:

1. Find `LOCAL_MODE=` and make sure it says: `LOCAL_MODE=true`
2. Find `ALLOW_INSECURE_DEFAULTS=` and make sure it says: `ALLOW_INSECURE_DEFAULTS=true`
3. Find `DATABASE_URL=` and change it to your shared database URL. It should look like:
   `DATABASE_URL=postgresql://postgres:postgres@192.168.1.100:5432/rag_brain`
   (Replace `192.168.1.100` with the IP address of Machine A where the database is running)
4. Find `OPENAI_API_KEY=` and set it to your OpenAI API key: `OPENAI_API_KEY=sk-your-actual-key-here`
5. Find `SECRET_KEY=` and generate a new one. Exit nano temporarily:
   - Press Ctrl+X
   - Type: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
   - Copy the output
   - Run: `nano .env` again
   - Paste the secret key after `SECRET_KEY=`

To save in nano: Press Ctrl+X, then press Y, then press Enter.

## Step 8: Test database connection

```bash
source .env
psql $DATABASE_URL -c "SELECT version();"
```

If this works, you'll see PostgreSQL version info. If it fails, check your DATABASE_URL in .env.

## Step 9: Initialize database schema

```bash
psql $DATABASE_URL < db_schema.sql
```

Wait for it to finish. This may take 30 seconds.

## Step 10: Start the server

```bash
source venv/bin/activate
./START_LOCAL.sh
```

Wait for it to say "Starting server on http://localhost:8000"

## Step 11: Open in browser

Open your browser and go to: http://localhost:8000/app

You're done. The server is running.

