#!/bin/bash
# Setup workspace tables in database
# Usage: ./SETUP_WORKSPACE_TABLES.sh

set -e

echo "🔧 Setting up workspace database tables..."
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL is not set!"
    echo ""
    echo "Please set it first:"
    echo "  export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
    echo ""
    echo "Or if using .env file:"
    echo "  source .env"
    exit 1
fi

echo "✅ DATABASE_URL is set"
echo ""

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "❌ psql command not found!"
    echo "Install PostgreSQL client: brew install postgresql"
    exit 1
fi

echo "✅ psql is available"
echo ""

# Run the schema
echo "📝 Creating tables from db_schema.sql..."
psql "$DATABASE_URL" -f db_schema.sql

echo ""
echo "✅ Tables created successfully!"
echo ""

# Verify tables
echo "🔍 Verifying tables exist..."
psql "$DATABASE_URL" -c "\dt" | grep -E "users|organizations|workspaces|workspace_members|workspace_settings"

echo ""
echo "🎉 Setup complete! You can now create workspaces."
echo ""
echo "Test it:"
echo "  1. Start server: python server.py"
echo "  2. Open: http://localhost:8000/app/"
echo "  3. Click workspace dropdown → Create New Workspace"


