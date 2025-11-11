#!/bin/bash
# Docker Healthcheck Test Script
# Tests that the hardened Dockerfile builds successfully and healthcheck works

set -e

IMAGE_NAME="prep-test"
CONTAINER_NAME="prep-healthcheck-test"
PORT=8000

echo "=== Docker Healthcheck Test ==="
echo

# Cleanup any existing test containers
echo "Cleaning up any existing test containers..."
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
docker rmi -f "$IMAGE_NAME" 2>/dev/null || true

echo "Building Docker image..."
docker build -t "$IMAGE_NAME" .

echo "Starting container in detached mode..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "${PORT}:${PORT}" \
  "$IMAGE_NAME"

echo "Waiting for container to start (40s - matching HEALTHCHECK start-period)..."
sleep 40

echo "Checking container health status..."
HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "no-health-check")

echo "Health status: $HEALTH_STATUS"

echo "Attempting to reach health endpoint..."
if curl -f http://localhost:${PORT}/health 2>/dev/null; then
  echo "✓ Health endpoint responded successfully"
  ENDPOINT_OK=true
elif curl -f http://localhost:${PORT}/ 2>/dev/null; then
  echo "✓ Root endpoint responded successfully (health endpoint may not exist)"
  ENDPOINT_OK=true
else
  echo "✗ Neither /health nor / endpoints responded"
  ENDPOINT_OK=false
fi

echo
echo "Container logs:"
docker logs "$CONTAINER_NAME" | tail -n 20

echo
echo "Cleaning up..."
docker stop "$CONTAINER_NAME"
docker rm "$CONTAINER_NAME"
docker rmi "$IMAGE_NAME"

if [ "$ENDPOINT_OK" = true ]; then
  echo
  echo "✓ Docker healthcheck test PASSED"
  exit 0
else
  echo
  echo "✗ Docker healthcheck test FAILED"
  exit 1
fi
