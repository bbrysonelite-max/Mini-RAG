#!/bin/bash
# Start server locally with correct DATABASE_URL for Docker Compose
# Usage: ./scripts/start_server_local.sh

set -e

echo "Starting Mini-RAG server for local development..."
echo ""

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
fi

# Override DATABASE_URL for local development
# Docker Compose exposes Postgres on localhost:5432
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/rag_brain"
export ALLOW_INSECURE_DEFAULTS="true"
export LOCAL_MODE="true"

echo "✓ DATABASE_URL set to: postgresql://postgres:postgres@localhost:5432/rag_brain"
echo "✓ LOCAL_MODE enabled (bypasses authentication for local dev)"
echo "✓ ALLOW_INSECURE_DEFAULTS enabled"
echo ""

# Check if database is accessible
echo "Checking database connection..."
if python3 -c "import psycopg; conn = psycopg.connect('$DATABASE_URL'); print('✓ Database accessible'); conn.close()" 2>/dev/null; then
    echo "✓ Database is ready"
else
    echo "⚠ Database might not be running. Start it with: docker compose up db"
    echo ""
fi

echo ""
echo "Starting server..."
echo "Server will be available at: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

# Start uvicorn
uvicorn server:app --reload --host 0.0.0.0 --port 8000

