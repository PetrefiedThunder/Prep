#!/bin/bash
# Simple wrapper for prepctl dev command

set -e

echo "🚀 Prep Platform - One-Command Dev Setup"
echo "========================================="
echo ""

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if prepctl is available
if ! command -v prepctl &> /dev/null; then
    echo "⚙️  Installing prepctl CLI..."
    pip install -e . > /dev/null 2>&1
fi

# Run prepctl dev
prepctl dev "$@"
