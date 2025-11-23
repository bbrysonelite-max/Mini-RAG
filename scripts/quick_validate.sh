#!/bin/bash
# Quick validation - runs in 5 minutes

set -e
cd "$(dirname "$0")/.."

echo "=========================================="
echo "Quick Validation Suite"
echo "=========================================="
echo ""

# 1. Check critical files exist
echo "✓ Checking files..."
test -f server.py && echo "  ✓ server.py"
test -f cache_service.py && echo "  ✓ cache_service.py"
test -f request_dedup.py && echo "  ✓ request_dedup.py"
test -f docs/ARCHITECTURE.md && echo "  ✓ Architecture docs"
test -f docs/SECURITY_AUDIT.md && echo "  ✓ Security audit"

# 2. Check Docker setup
echo ""
echo "✓ Checking Docker..."
if command -v docker &> /dev/null; then
    echo "  ✓ Docker installed"
    if docker compose version &> /dev/null; then
        echo "  ✓ Docker Compose available"
    fi
else
    echo "  ⚠ Docker not found (optional for local dev)"
fi

# 3. Check Python syntax
echo ""
echo "✓ Checking Python syntax..."
python3 -m py_compile server.py 2>&1 | grep -v "^$" || echo "  ✓ server.py syntax OK"
python3 -m py_compile cache_service.py 2>&1 | grep -v "^$" || echo "  ✓ cache_service.py syntax OK"
python3 -m py_compile request_dedup.py 2>&1 | grep -v "^$" || echo "  ✓ request_dedup.py syntax OK"

# 4. Check scripts are executable
echo ""
echo "✓ Checking scripts..."
test -x scripts/smoke_test.sh && echo "  ✓ smoke_test.sh executable"
test -x scripts/validate_production_env.py && echo "  ✓ validate_production_env.py executable"

# 5. Check documentation completeness
echo ""
echo "✓ Checking documentation..."
grep -q "DEPLOYMENT_CHECKLIST" docs/guides/DEPLOYMENT_CHECKLIST.md && echo "  ✓ Deployment checklist"
grep -q "TROUBLESHOOTING" docs/guides/TROUBLESHOOTING.md && echo "  ✓ Troubleshooting guide"
grep -q "PERFORMANCE_TUNING" docs/guides/PERFORMANCE_TUNING.md && echo "  ✓ Performance guide"

echo ""
echo "=========================================="
echo "✅ Basic validation complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Set environment variables (see env.template)"
echo "2. Start services: docker-compose up"
echo "3. Run smoke tests: ./scripts/smoke_test.sh"
echo ""

