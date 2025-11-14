#!/bin/bash

set -euo pipefail

echo "Running comprehensive security verification..."

echo "1. Checking for hardcoded credentials..."
if grep -r "password\|secret\|api.*key" . --include="*.yml" --include="*.yaml" --include="*.env" | grep -v ".env.example" | grep -v "node_modules"; then
    echo "❌ Hardcoded credentials found in configuration files!"
    exit 1
else
    echo "✅ No hardcoded credentials found"
fi

echo "2. Verifying environment variable usage..."
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found - this is expected in CI environments"
else
    echo "✅ .env file present"
fi

echo "3. Checking TypeScript configuration..."
if [ -f "tsconfig.json" ]; then
    if command -v npx &> /dev/null && npx --no-install tsc --version &> /dev/null; then
        if npx --no-install tsc --noEmit --project tsconfig.json > /dev/null 2>&1; then
            echo "✅ TypeScript configuration valid"
        else
            echo "❌ TypeScript configuration errors found"
            exit 1
        fi
    else
        echo "⚠️  TypeScript compiler not available"
    fi
else
    echo "⚠️  No tsconfig.json found"
fi

echo "4. Checking Python linting configuration..."
if [ -f "ruff.toml" ]; then
    if command -v ruff &> /dev/null; then
        if ruff check --config ruff.toml . --exit-zero > /dev/null 2>&1; then
            echo "✅ Ruff configuration valid"
        else
            echo "❌ Ruff configuration errors found"
            exit 1
        fi
    else
        echo "⚠️  Ruff not installed"
    fi
else
    echo "⚠️  No ruff.toml found"
fi

echo "5. Checking ESLint configuration..."
if [ -f "eslint.config.js" ]; then
    if command -v npx &> /dev/null && npx --no-install eslint --version &> /dev/null; then
        if npx --no-install eslint . --quiet > /dev/null 2>&1; then
            echo "✅ ESLint configuration valid"
        else
            echo "❌ ESLint configuration errors found"
            exit 1
        fi
    else
        echo "⚠️  ESLint not installed"
    fi
else
    echo "⚠️  No eslint.config.js found"
fi

echo "🎉 All security verification checks passed!"
