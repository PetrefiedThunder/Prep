# ===================================
# Stage 1: Builder
# ===================================
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy and install Python dependencies
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# ===================================
# Stage 2: Runtime
# ===================================
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for application
RUN groupadd -r prepapp --gid=1000 && \
    useradd -r -g prepapp --uid=1000 --home-dir=/app --shell=/bin/bash prepapp

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder --chown=prepapp:prepapp /root/.local /home/prepapp/.local

# Copy application code
COPY --chown=prepapp:prepapp . .

# Set PATH to include user-installed Python packages
ENV PATH=/home/prepapp/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER prepapp

# Expose application port
EXPOSE 8000

# Health check - adjust endpoint if your app uses different health route
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || curl -f http://localhost:8000/ || exit 1

# Run application
CMD ["uvicorn", "prep.main:app", "--host", "0.0.0.0", "--port", "8000"]
