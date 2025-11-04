#!/bin/bash
# Bootstrap script for Prep development environment
set -euo pipefail

echo "🚀 Starting Prep development environment setup..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1) Python 3.11 venv
echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD=python3.11
elif command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    echo "Error: Python 3 not found"
    exit 1
fi

$PYTHON_CMD -m venv .venv
source .venv/bin/activate
python -m pip install -U pip --quiet

# 2) Resolve AWS libs conflict - requirements.txt now has correct pins
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt --upgrade --upgrade-strategy eager --quiet
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# 3) Node LTS
echo -e "${YELLOW}Setting up Node dependencies...${NC}"

# Detect Node path (support both Homebrew and standard installations)
if [ -d "/opt/homebrew/opt/node@20/bin" ]; then
    export PATH="/opt/homebrew/opt/node@20/bin:$PATH"
fi

if ! command -v node &> /dev/null; then
    echo "Error: Node.js not found. Please install Node 20+"
    exit 1
fi

echo "Using Node $(node -v) and npm $(npm -v)"

# Install prepchef dependencies
if [ -d "prepchef" ]; then
    echo "Installing prepchef dependencies..."
    ( cd prepchef && rm -rf node_modules package-lock.json && npm ci --quiet )
    echo -e "${GREEN}✓ prepchef dependencies installed${NC}"
fi

# Install harborhomes dependencies
if [ -d "apps/harborhomes" ]; then
    echo "Installing harborhomes dependencies..."
    ( cd apps/harborhomes && rm -rf node_modules package-lock.json && npm ci --quiet )
    echo -e "${GREEN}✓ harborhomes dependencies installed${NC}"
fi

# 4) Env + docker
echo -e "${YELLOW}Setting up environment and Docker...${NC}"
[ -f .env ] || cp .env.example .env

if ! command -v docker &> /dev/null; then
    echo "Warning: Docker not found. Skipping container setup."
else
    echo "Building and starting Docker containers..."
    docker compose up -d --build
    echo -e "${GREEN}✓ Docker containers started${NC}"

    # 5) Smoke checks
    echo -e "${YELLOW}Running health checks...${NC}"
    sleep 5

    if curl -sf http://localhost:8000/docs >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Python API OK (port 8000)${NC}"
    else
        echo -e "${YELLOW}⚠ Python API not responding on port 8000${NC}"
    fi

    if curl -sf http://localhost:3000 >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Node API OK (port 3000)${NC}"
    else
        echo -e "${YELLOW}⚠ Node API not responding on port 3000${NC}"
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Development environment ready!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Services:"
echo "  • Portal: http://localhost:3000"
echo "  • Python API: http://localhost:8000/docs"
echo "  • Postgres: localhost:5432"
echo "  • Redis: localhost:6379"
echo "  • MinIO: http://localhost:9001"
echo ""
echo "To activate Python environment: source .venv/bin/activate"
echo "To view logs: docker compose logs -f"
echo "To stop services: docker compose down"
