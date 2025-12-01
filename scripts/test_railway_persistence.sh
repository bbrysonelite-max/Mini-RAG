#!/bin/bash
# Test chunk persistence on Railway
# This runs inside Railway's network where .railway.internal hostnames work

set -e

echo "============================================================"
echo "Testing Railway Chunk Persistence"
echo "============================================================"
echo ""

# Run the test script inside Railway
echo "Running persistence test inside Railway..."
railway run python3 scripts/test_persistence.py

echo ""
echo "============================================================"
echo "If chunks are found, persistence is working!"
echo "============================================================"

