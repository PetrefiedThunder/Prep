#!/bin/bash

# Secret Detection Script for PrepChef
# This script scans for accidentally exposed secrets in the codebase
# Usage: ./scripts/check_secrets.sh
# Exit code: 0 = no secrets found, 1 = secrets detected

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

ERRORS=0

echo "🔍 Scanning for exposed secrets..."

# Function to check for secrets in a pattern
check_pattern() {
    local pattern="$1"
    local description="$2"
    local files="$3"

    if grep -rn --color=always -E "$pattern" $files 2>/dev/null | grep -v "scripts/check_secrets.sh"; then
        echo -e "${RED}❌ FOUND: $description${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
    return 0
}

# 1. Check for Stripe secret keys in .env files
echo ""
echo "1️⃣  Checking .env files for Stripe secrets..."
if find . -name "*.env" -o -name ".env.*" 2>/dev/null | xargs grep -l "STRIPE_SECRET" 2>/dev/null | grep -v ".env.example"; then
    # Check if it contains actual secret keys (not placeholders)
    if find . -name "*.env" -o -name ".env.*" 2>/dev/null | xargs grep -E "sk_live_|sk_test_[a-zA-Z0-9]{24,}" 2>/dev/null | grep -v ".env.example"; then
        echo -e "${RED}❌ FOUND: Stripe secret keys in .env files${NC}"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✓ .env files contain STRIPE_SECRET but appear to be placeholders${NC}"
    fi
else
    echo -e "${GREEN}✓ No Stripe secrets in .env files${NC}"
fi

# 2. Check for hardcoded Stripe keys in source code
echo ""
echo "2️⃣  Checking source code for hardcoded Stripe keys..."
check_pattern "sk_(test|live)_[a-zA-Z0-9]{24,}" \
    "Hardcoded Stripe secret keys" \
    "--include=*.py --include=*.js --include=*.ts --include=*.jsx --include=*.tsx ." || true

# 3. Check for Stripe webhook secrets
echo ""
echo "3️⃣  Checking for hardcoded Stripe webhook secrets..."
check_pattern "whsec_[a-zA-Z0-9]{32,}" \
    "Hardcoded Stripe webhook secrets" \
    "--include=*.py --include=*.js --include=*.ts --include=*.jsx --include=*.tsx ." || true

# 4. Check for AWS access keys
echo ""
echo "4️⃣  Checking for AWS access keys..."
check_pattern "AKIA[0-9A-Z]{16}" \
    "AWS access key IDs" \
    "--include=*.py --include=*.js --include=*.ts --include=*.jsx --include=*.tsx --include=*.env* ." || true

# 5. Check for JWT secrets (long random strings in code)
echo ""
echo "5️⃣  Checking for hardcoded JWT secrets..."
if grep -rn --color=always -E "(JWT_SECRET|jwtSecret)['\"]?\s*[:=]\s*['\"][a-zA-Z0-9+/=]{32,}['\"]" \
    --include=*.py --include=*.js --include=*.ts --include=*.jsx --include=*.tsx . 2>/dev/null | \
    grep -v "test" | grep -v "example" | grep -v ".env.example" | grep -v "scripts/check_secrets.sh"; then
    echo -e "${RED}❌ FOUND: Hardcoded JWT secrets${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ No hardcoded JWT secrets${NC}"
fi

# 6. Check for database passwords in code
echo ""
echo "6️⃣  Checking for hardcoded database passwords..."
if grep -rn --color=always -E "postgres://[^:]+:[^@]{8,}@" \
    --include=*.py --include=*.js --include=*.ts --include=*.jsx --include=*.tsx . 2>/dev/null | \
    grep -v "example" | grep -v "test" | grep -v "placeholder" | grep -v "scripts/check_secrets.sh"; then
    echo -e "${RED}❌ FOUND: Hardcoded database connection strings with passwords${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ No hardcoded database passwords${NC}"
fi

# 7. Check for private keys
echo ""
echo "7️⃣  Checking for private keys..."
check_pattern "-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----" \
    "Private keys" \
    "--include=*.py --include=*.js --include=*.ts --include=*.tsx --include=*.pem --include=*.key ." || true

# 8. Check for API keys in common formats
echo ""
echo "8️⃣  Checking for generic API keys..."
if grep -rn --color=always -E "(api_key|apikey|api-key)['\"]?\s*[:=]\s*['\"][a-zA-Z0-9]{20,}['\"]" \
    --include=*.py --include=*.js --include=*.ts --include=*.jsx --include=*.tsx . 2>/dev/null | \
    grep -v "test" | grep -v "example" | grep -v "placeholder" | grep -v "scripts/check_secrets.sh" | \
    grep -v "YOUR_API_KEY" | grep -v "your-api-key"; then
    echo -e "${YELLOW}⚠️  WARNING: Possible API keys found (review manually)${NC}"
else
    echo -e "${GREEN}✓ No obvious API keys${NC}"
fi

# 9. Check for MinIO/S3 credentials
echo ""
echo "9️⃣  Checking for MinIO/S3 access keys in code..."
if grep -rn --color=always -E "(MINIO_SECRET_KEY|AWS_SECRET_ACCESS_KEY)['\"]?\s*[:=]\s*['\"][a-zA-Z0-9+/]{20,}['\"]" \
    --include=*.py --include=*.js --include=*.ts --include=*.jsx --include=*.tsx . 2>/dev/null | \
    grep -v "test" | grep -v "example" | grep -v ".env.example" | grep -v "scripts/check_secrets.sh" | \
    grep -v "placeholder"; then
    echo -e "${RED}❌ FOUND: Hardcoded MinIO/S3 credentials${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ No hardcoded MinIO/S3 credentials${NC}"
fi

# 10. Check for .env files in git staging area
echo ""
echo "🔟 Checking git staging area for .env files..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    if git diff --cached --name-only | grep -E "\.env$|\.env\..*" | grep -v ".env.example"; then
        echo -e "${RED}❌ FOUND: .env files staged for commit${NC}"
        echo -e "${YELLOW}Run: git reset HEAD <file> to unstage${NC}"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✓ No .env files in staging area${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Not a git repository, skipping git checks${NC}"
fi

echo ""
echo "═════════════════════════════════════════════════════════"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ SUCCESS: No secrets detected!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}❌ FAILURE: $ERRORS secret(s) detected!${NC}"
    echo ""
    echo "Please remove the exposed secrets and use environment variables instead."
    echo "See SECURITY.md for proper secret management practices."
    echo ""
    exit 1
fi
