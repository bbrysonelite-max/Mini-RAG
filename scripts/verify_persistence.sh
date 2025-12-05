#!/bin/bash
# Verify chunk persistence test
# Run this before and after Railway redeploy

set -e

echo "============================================================"
echo "Chunk Persistence Verification"
echo "============================================================"
echo ""

# Check if we're testing local or Railway
if [ -z "${DATABASE_URL:-}" ]; then
    echo "Using local database..."
    export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/rag_brain"
else
    echo "Using Railway database..."
fi

echo "DATABASE_URL: ${DATABASE_URL:0:60}..."
echo ""

# Activate venv if available
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the persistence test
python3 scripts/test_persistence.py

echo ""
echo "============================================================"
echo "Next Steps:"
echo "============================================================"
echo ""
echo "1. If testing Railway persistence:"
echo "   - Deploy to Railway: git push"
echo "   - Wait for redeploy to complete"
echo "   - Run this script again with Railway DATABASE_URL:"
echo "     DATABASE_URL='railway_url' ./scripts/verify_persistence.sh"
echo ""
echo "2. Expected result: Chunks should persist because they're"
echo "   stored in PostgreSQL (persistent), not ephemeral filesystem"
echo ""




