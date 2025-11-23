#!/bin/bash
# Quick security check before production deploy

set -e
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "Security Audit - Quick Pass"
echo "=========================================="
echo ""

ISSUES=0

# 1. Check for placeholder secrets in .env
echo "Checking .env for placeholders..."
if [ -f .env ]; then
    if grep -qi "placeholder\|changeme\|your-\|example" .env; then
        echo -e "${RED}✗ FAIL: Found placeholder values in .env${NC}"
        grep -i "placeholder\|changeme\|your-\|example" .env | head -5
        ((ISSUES++))
    else
        echo -e "${GREEN}✓ PASS: No placeholders in .env${NC}"
    fi
else
    echo -e "${YELLOW}⚠ WARNING: .env file not found${NC}"
fi

# 2. Check for secrets in git
echo ""
echo "Checking for committed secrets..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    if git grep -i "sk_live\|sk_test.*[a-zA-Z0-9]{20,}\|password.*=.*[a-zA-Z]" -- '*.py' '*.md' '*.yml' > /dev/null 2>&1; then
        echo -e "${RED}✗ FAIL: Found potential secrets in git${NC}"
        ((ISSUES++))
    else
        echo -e "${GREEN}✓ PASS: No secrets in git${NC}"
    fi
fi

# 3. Check .gitignore includes sensitive files
echo ""
echo "Checking .gitignore..."
if [ -f .gitignore ]; then
    if grep -q ".env" .gitignore && grep -q "chunks.jsonl" .gitignore; then
        echo -e "${GREEN}✓ PASS: Sensitive files gitignored${NC}"
    else
        echo -e "${YELLOW}⚠ WARNING: .gitignore may be incomplete${NC}"
    fi
fi

# 4. Check for demo data
echo ""
echo "Checking for demo data..."
if [ -f out/chunks.jsonl ]; then
    echo -e "${YELLOW}⚠ WARNING: out/chunks.jsonl exists (demo data?)${NC}"
    echo "  Consider deleting before production"
else
    echo -e "${GREEN}✓ PASS: No demo chunks.jsonl${NC}"
fi

# 5. Check Python dependencies
echo ""
echo "Checking dependencies..."
if command -v pip-audit &> /dev/null; then
    echo "Running pip-audit..."
    if pip-audit --desc -r requirements.txt 2>&1 | grep -i "critical\|high"; then
        echo -e "${RED}✗ WARNING: Vulnerable dependencies found${NC}"
        ((ISSUES++))
    else
        echo -e "${GREEN}✓ PASS: No critical vulnerabilities${NC}"
    fi
else
    echo -e "${YELLOW}⚠ SKIP: pip-audit not installed${NC}"
    echo "  Install: pip3 install pip-audit"
fi

# 6. Check Docker security
echo ""
echo "Checking Dockerfile..."
if grep -q "USER" Dockerfile; then
    echo -e "${GREEN}✓ PASS: Non-root user in Dockerfile${NC}"
else
    echo -e "${YELLOW}⚠ WARNING: Dockerfile may run as root${NC}"
    echo "  Consider adding: USER nonroot"
fi

# 7. Check for SQL injection patterns
echo ""
echo "Checking for SQL injection risks..."
if grep -r "execute.*format\|execute.*%" --include="*.py" . | grep -v "test_\|#"; then
    echo -e "${RED}✗ WARNING: Potential string formatting in SQL${NC}"
    ((ISSUES++))
else
    echo -e "${GREEN}✓ PASS: Using parameterized queries${NC}"
fi

# 8. Check security headers configured
echo ""
echo "Checking security middleware..."
if grep -q "CSP\|Content-Security-Policy" server.py; then
    echo -e "${GREEN}✓ PASS: Security headers configured${NC}"
else
    echo -e "${YELLOW}⚠ WARNING: Security headers may be missing${NC}"
fi

# Summary
echo ""
echo "=========================================="
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ Security audit passed!${NC}"
    echo "No critical issues found."
    exit 0
else
    echo -e "${YELLOW}⚠️ $ISSUES issue(s) found${NC}"
    echo "Review and fix before production deploy."
    echo ""
    echo "See docs/SECURITY_AUDIT.md for full checklist."
    exit 1
fi

