#!/bin/bash
# Start Mini-RAG locally without Docker

set -e

echo "=========================================="
echo "🚀 Starting Mini-RAG Locally"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from your template..."
    cp PRODUCTION_ENV_TEMPLATE .env
    echo "✓ Created .env - edit if needed"
fi

# Source environment
set -a
source .env
set +a

# Simple mode: disable optional services for faster dev iteration
export LOCAL_MODE=true
export ALLOW_INSECURE_DEFAULTS=true
# Keep DATABASE_URL and OPENAI_API_KEY from .env
unset ANTHROPIC_API_KEY MINI_RAG_API_KEY REDIS_URL

echo "Environment loaded:"
echo "  ✓ GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID:0:20}..."
echo "  ✓ SECRET_KEY: ${SECRET_KEY:0:10}..."
echo "  ✓ OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
echo ""

# Check if we need to use venv
if [ -d "venv" ] && [ -f "venv/bin/python" ]; then
    echo "Using virtual environment..."
    PYTHON="./venv/bin/python"
    UVICORN="./venv/bin/uvicorn"
else
    echo "Using system Python..."
    PYTHON="python3"
    UVICORN="uvicorn"
fi

# Check if uvicorn is available
if ! command -v $UVICORN &> /dev/null; then
    echo "Installing uvicorn..."
    $PYTHON -m pip install uvicorn
fi

echo ""
echo "Starting server on http://localhost:8000"
echo ""
echo "  Web UI: http://localhost:8000/app"
echo "  API Docs: http://localhost:8000/docs"
echo "  Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start server
$PYTHON -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload



