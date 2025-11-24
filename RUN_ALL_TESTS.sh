#!/bin/bash
# Comprehensive test suite - runs EVERYTHING

set -e

cd "$(dirname "$0")"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "🧪 COMPREHENSIVE TEST SUITE"
echo "=========================================="
echo ""
date
echo ""

# Set test environment
export ALLOW_INSECURE_DEFAULTS=true
export REDIS_ENABLED=false  # Test without Redis first

TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0

# Helper function
run_test_suite() {
    local name="$1"
    local command="$2"
    
    echo -e "${BLUE}━━━ $name ━━━${NC}"
    
    if eval "$command" > /tmp/test_output.txt 2>&1; then
        local passed=$(grep -o "[0-9]* passed" /tmp/test_output.txt | head -1 | awk '{print $1}')
        local skipped=$(grep -o "[0-9]* skipped" /tmp/test_output.txt | head -1 | awk '{print $1}')
        
        passed=${passed:-0}
        skipped=${skipped:-0}
        
        echo -e "${GREEN}✅ PASS${NC} - $passed passed, $skipped skipped"
        TOTAL_PASSED=$((TOTAL_PASSED + passed))
        TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))
        return 0
    else
        local failed=$(grep -o "[0-9]* failed" /tmp/test_output.txt | head -1 | awk '{print $1}')
        local passed=$(grep -o "[0-9]* passed" /tmp/test_output.txt | head -1 | awk '{print $1}')
        
        failed=${failed:-1}
        passed=${passed:-0}
        
        echo -e "${RED}❌ FAIL${NC} - $failed failed, $passed passed"
        echo "  See /tmp/test_output.txt for details"
        
        # Show failures
        grep "FAILED" /tmp/test_output.txt | head -5 || true
        
        TOTAL_FAILED=$((TOTAL_FAILED + failed))
        TOTAL_PASSED=$((TOTAL_PASSED + passed))
        return 1
    fi
    echo ""
}

# 1. Core RAG Pipeline
run_test_suite "Core RAG Pipeline" \
    "./venv/bin/pytest test_rag_pipeline.py -v --tb=line"

# 2. Authentication & Authorization
run_test_suite "Auth & Authorization" \
    "./venv/bin/pytest test_api_key_auth.py test_phase3_auth.py -v --tb=line"

# 3. Quota Service
run_test_suite "Quota Service" \
    "./venv/bin/pytest test_quota_service.py -v --tb=line"

# 4. Billing Guards
run_test_suite "Billing Guards" \
    "./venv/bin/pytest test_billing_guard.py -v --tb=line"

# 5. Cache Service (NEW)
run_test_suite "Cache Service" \
    "./venv/bin/pytest tests/test_cache_service.py -v --tb=line"

# 6. Request Dedup (NEW)
run_test_suite "Request Deduplication" \
    "./venv/bin/pytest tests/test_request_dedup.py -v --tb=line"

# 7. E2E Auth Tests (NEW)
run_test_suite "E2E Auth Flow" \
    "./venv/bin/pytest tests/test_auth_e2e.py -v --tb=line"

# 8. Admin API
run_test_suite "Admin API" \
    "./venv/bin/pytest tests/test_admin_api.py -v --tb=line"

# 9. SDK Tests
run_test_suite "Python SDK" \
    "./venv/bin/pytest tests/test_sdk.py -v --tb=line"

# 10. Security Headers
run_test_suite "Security Headers" \
    "./venv/bin/pytest tests/test_security_headers.py -v --tb=line"

# 11. Metrics Endpoint
run_test_suite "Metrics Endpoint" \
    "./venv/bin/pytest tests/test_metrics_endpoint.py -v --tb=line"

# 12. Background Queue
run_test_suite "Background Job Queue" \
    "./venv/bin/pytest tests/test_background_queue.py -v --tb=line"

echo ""
echo "=========================================="
echo "📊 TEST SUMMARY"
echo "=========================================="
echo -e "${GREEN}Passed:  $TOTAL_PASSED${NC}"
echo -e "${YELLOW}Skipped: $TOTAL_SKIPPED${NC}"
echo -e "${RED}Failed:  $TOTAL_FAILED${NC}"
echo ""

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSING!${NC}"
    echo ""
    echo "Your codebase is solid. Ready for:"
    echo "  1. Manual UI testing"
    echo "  2. Load testing"
    echo "  3. Production deployment"
    echo ""
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Review failures above and fix before deploying."
    echo ""
    exit 1
fi


