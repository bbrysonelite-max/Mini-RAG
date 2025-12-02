#!/bin/bash
# Simple script to test database connection
# Usage: ./scripts/test_db_simple.sh

set -e

echo "=" 
echo "Database Connection Test"
echo "="

# Check if venv exists and activate it
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check for DATABASE_URL
if [ -z "${DATABASE_URL:-}" ]; then
    echo ""
    echo "❌ DATABASE_URL not set!"
    echo ""
    echo "To get your Railway DATABASE_URL:"
    echo "  1. Go to Railway dashboard: https://railway.app"
    echo "  2. Select your project"
    echo "  3. Go to your Postgres service"
    echo "  4. Copy the 'Public URL' or 'Connection URL'"
    echo ""
    echo "Then run:"
    echo "  export DATABASE_URL='postgresql://user:password@host:port/database'"
    echo "  python3 scripts/test_database.py"
    echo ""
    exit 1
fi

echo "✓ DATABASE_URL is set"
echo ""

# Run the test
python3 scripts/test_database.py


