#!/bin/bash
# Smoke test script for post-deployment validation
# Run this after deploying to verify critical functionality

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
API_KEY="${MINI_RAG_API_KEY:-}"

echo "=========================================="
echo "Mini-RAG Smoke Test Suite"
echo "=========================================="
echo "Target: $BASE_URL"
echo ""

FAILED_TESTS=0
PASSED_TESTS=0

# Helper function to run test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing: $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED_TESTS++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
}

# Test 1: Health endpoint
run_test "Health check" \
    "curl -f -s $BASE_URL/health | grep -q '\"status\":\"ok\"'"

# Test 2: Metrics endpoint
run_test "Metrics endpoint" \
    "curl -f -s $BASE_URL/metrics | grep -q 'ask_requests_total'"

# Test 3: OAuth redirect (should 302)
run_test "OAuth redirect" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/auth/google | grep -q '^302$'"

# Test 4: Protected endpoint without auth (should 401)
run_test "Auth protection" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/ask | grep -q '^401$'"

# Test 5: Stats endpoint (may require auth depending on config)
run_test "Stats endpoint" \
    "curl -f -s $BASE_URL/api/v1/stats | grep -q '\"count\"'"

# Test 6: OpenAPI docs
run_test "OpenAPI docs" \
    "curl -f -s $BASE_URL/docs | grep -q 'Mini-RAG'"

# If API key is provided, test authenticated endpoints
if [ -n "$API_KEY" ]; then
    echo ""
    echo "Running authenticated tests..."
    
    # Test 7: Authenticated ask endpoint
    run_test "Ask endpoint (auth)" \
        "curl -f -s -X POST $BASE_URL/api/v1/ask \
         -H 'X-API-Key: $API_KEY' \
         -F 'query=test' \
         -F 'k=5' | grep -q '\"answer\"'"
    
    # Test 8: Sources list
    run_test "Sources endpoint" \
        "curl -f -s $BASE_URL/api/v1/sources \
         -H 'X-API-Key: $API_KEY' | grep -q '\"sources\"'"
    
    # Test 9: Admin workspaces (may fail if not admin key)
    if curl -f -s $BASE_URL/api/v1/admin/workspaces -H "X-API-Key: $API_KEY" > /dev/null 2>&1; then
        echo -e "Testing: Admin workspaces... ${GREEN}✓ PASS${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "Testing: Admin workspaces... ${YELLOW}⚠ SKIP (requires admin scope)${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}⚠ No API key provided - skipping authenticated tests${NC}"
    echo "Set MINI_RAG_API_KEY to run full test suite"
fi

# Database connectivity test (if health check passed)
echo ""
echo -n "Testing: Database connectivity... "
DB_STATUS=$(curl -s $BASE_URL/health | grep -o '"database":"[^"]*"' | cut -d'"' -f4)
if [ "$DB_STATUS" = "connected" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED_TESTS++))
elif [ "$DB_STATUS" = "not_configured" ]; then
    echo -e "${YELLOW}⚠ SKIP (database not configured)${NC}"
else
    echo -e "${RED}✗ FAIL (status: $DB_STATUS)${NC}"
    ((FAILED_TESTS++))
fi

# Index loaded test
echo -n "Testing: Index loaded... "
INDEX_STATUS=$(curl -s $BASE_URL/health | grep -o '"index_loaded":[^,}]*' | cut -d':' -f2)
if [ "$INDEX_STATUS" = "true" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED_TESTS++))
else
    echo -e "${YELLOW}⚠ WARNING (index not loaded)${NC}"
fi

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ All critical tests passed!${NC}"
    echo "Deployment appears healthy."
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    echo "Review errors above before proceeding."
    exit 1
fi

