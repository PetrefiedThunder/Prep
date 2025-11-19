#!/bin/bash
set -euo pipefail

# Microservices Security Scanner
# This script scans all Node.js microservices for security vulnerabilities

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICES_DIR="$REPO_ROOT/prepchef/services"
RESULTS_DIR="$REPO_ROOT/scan-results"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service list
SERVICES=(
    "access-svc"
    "admin-svc"
    "audit-svc"
    "auth-svc"
    "availability-svc"
    "booking-svc"
    "compliance-svc"
    "listing-svc"
    "notif-svc"
    "payments-svc"
    "pricing-svc"
)

# Counters
TOTAL_SERVICES=${#SERVICES[@]}
SCANNED_SERVICES=0
VULNERABLE_SERVICES=0

print_header() {
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================================${NC}"
}

print_section() {
    echo -e "\n${YELLOW}>>> $1${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Create results directory
mkdir -p "$RESULTS_DIR"

print_header "Microservices Security Scanner"
echo "Scanning $TOTAL_SERVICES microservices..."
echo "Results will be saved to: $RESULTS_DIR"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 20+ to continue."
    exit 1
fi

print_success "Node.js $(node --version) detected"

# Function to scan a single service
scan_service() {
    local service=$1
    local service_dir="$SERVICES_DIR/$service"
    local has_vulnerabilities=false
    
    print_section "Scanning $service"
    
    if [ ! -d "$service_dir" ]; then
        print_error "Service directory not found: $service_dir"
        return 1
    fi
    
    cd "$service_dir"
    
    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        print_warning "No package.json found in $service"
        return 0
    fi
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing dependencies for $service..."
        npm ci --ignore-scripts --silent || npm install --silent || true
    fi
    
    # Run npm audit
    echo "Running npm audit..."
    if npm audit --audit-level=moderate > "$RESULTS_DIR/${service}_npm_audit.txt" 2>&1; then
        print_success "No vulnerabilities found in dependencies"
    else
        print_warning "Vulnerabilities found in dependencies (see $RESULTS_DIR/${service}_npm_audit.txt)"
        has_vulnerabilities=true
    fi
    
    # Run npm audit with JSON output
    npm audit --json > "$RESULTS_DIR/${service}_npm_audit.json" 2>&1 || true
    
    # Check for outdated packages
    echo "Checking for outdated packages..."
    npm outdated --json > "$RESULTS_DIR/${service}_outdated.json" 2>&1 || true
    
    # Run ESLint security scan if source files exist
    if [ -d "src" ]; then
        echo "Running ESLint security scan..."
        
        # Install ESLint and security plugin if not present
        if [ ! -d "node_modules/eslint-plugin-security" ]; then
            npm install --no-save --silent eslint eslint-plugin-security @typescript-eslint/parser 2>/dev/null || true
        fi
        
        # Create ESLint flat config for security scanning
        cat > eslint.config.scan.mjs <<'EOF'
import security from 'eslint-plugin-security';
import tsParser from '@typescript-eslint/parser';

export default [
  {
    files: ['src/**/*.ts', 'src/**/*.js'],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        console: 'readonly',
        process: 'readonly',
        Buffer: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        require: 'readonly',
        module: 'readonly',
        exports: 'readonly'
      }
    },
    plugins: {
      security
    },
    rules: {
      'security/detect-object-injection': 'warn',
      'security/detect-non-literal-regexp': 'warn',
      'security/detect-unsafe-regex': 'error',
      'security/detect-buffer-noassert': 'error',
      'security/detect-child-process': 'warn',
      'security/detect-eval-with-expression': 'error',
      'security/detect-non-literal-fs-filename': 'warn',
      'security/detect-non-literal-require': 'warn',
      'security/detect-possible-timing-attacks': 'warn',
      'security/detect-pseudoRandomBytes': 'error'
    }
  }
];
EOF
        
        # Run ESLint with the temporary config
        if ESLINT_USE_FLAT_CONFIG=true npx eslint src -c eslint.config.scan.mjs \
            > "$RESULTS_DIR/${service}_eslint.txt" 2>&1; then
            print_success "No security issues found in code"
        else
            print_warning "Security issues found in code (see $RESULTS_DIR/${service}_eslint.txt)"
            has_vulnerabilities=true
        fi
        
        # Clean up temporary config
        rm -f eslint.config.scan.mjs
    fi
    
    # Scan Dockerfile if it exists
    if [ -f "Dockerfile" ]; then
        echo "Scanning Dockerfile..."
        
        # Check for common Dockerfile security issues
        local dockerfile_issues=0
        
        # Check if running as root
        if ! grep -q "USER" Dockerfile; then
            print_warning "Dockerfile does not set USER (running as root)"
            dockerfile_issues=$((dockerfile_issues + 1))
        fi
        
        # Check for pinned base image
        if grep -q "FROM.*:latest" Dockerfile; then
            print_warning "Dockerfile uses :latest tag (should use pinned versions)"
            dockerfile_issues=$((dockerfile_issues + 1))
        fi
        
        if [ $dockerfile_issues -eq 0 ]; then
            print_success "Dockerfile follows security best practices"
        else
            has_vulnerabilities=true
        fi
    fi
    
    SCANNED_SERVICES=$((SCANNED_SERVICES + 1))
    
    if [ "$has_vulnerabilities" = true ]; then
        VULNERABLE_SERVICES=$((VULNERABLE_SERVICES + 1))
        print_error "Service $service has security concerns"
    else
        print_success "Service $service scan complete - no issues found"
    fi
    
    echo ""
}

# Scan all services
for service in "${SERVICES[@]}"; do
    scan_service "$service"
done

# Generate summary
print_header "Scan Summary"
echo "Total services scanned: $SCANNED_SERVICES / $TOTAL_SERVICES"
echo "Services with vulnerabilities: $VULNERABLE_SERVICES"
echo ""

if [ $VULNERABLE_SERVICES -eq 0 ]; then
    print_success "All microservices are secure!"
    echo ""
    echo "Results saved to: $RESULTS_DIR"
    exit 0
else
    print_warning "$VULNERABLE_SERVICES service(s) have security concerns"
    echo ""
    echo "Please review the results in: $RESULTS_DIR"
    echo ""
    echo "To fix vulnerabilities:"
    echo "  1. Review the audit reports in $RESULTS_DIR"
    echo "  2. Run 'npm audit fix' in affected service directories"
    echo "  3. Update vulnerable dependencies manually if needed"
    echo "  4. Re-run this script to verify fixes"
    exit 1
fi
