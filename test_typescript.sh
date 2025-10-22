#!/bin/bash
# test_typescript.sh

set -euo pipefail

echo "Testing TypeScript configuration..."

rm -rf dist

if command -v npx &> /dev/null && npx --no-install tsc --version &> /dev/null; then
    if npx --no-install tsc --noEmit --strict; then
        echo "\u2713 TypeScript compilation successful"
    else
        echo "\u2717 TypeScript compilation failed"
        exit 1
    fi

    if npx --no-install tsc --noEmit; then
        echo "\u2713 All type checks passed"
    else
        echo "\u2717 Type checking failed"
        exit 1
    fi
else
    echo "⚠️  TypeScript compiler not available"
fi

echo "TypeScript configuration validation complete!"
