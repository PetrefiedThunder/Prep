#!/bin/bash
# setup_dev_env.sh

set -euo pipefail

echo "Setting up secure development environment..."

if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env

    # Generate secure passwords
    export POSTGRES_PASS=$(openssl rand -base64 32 | tr -d '/=+' | cut -c -16)
    export REDIS_PASS=$(openssl rand -base64 32 | tr -d '/=+' | cut -c -16)
    export MINIO_PASS=$(openssl rand -base64 32 | tr -d '/=+' | cut -c -16)
    export PGADMIN_PASS=$(openssl rand -base64 32 | tr -d '/=+' | cut -c -16)

    python3 - <<'PY'
import os
from pathlib import Path

env_path = Path('.env')
lines = env_path.read_text().splitlines()
replacements = {
    'POSTGRES_PASSWORD': os.environ['POSTGRES_PASS'],
    'REDIS_PASSWORD': os.environ['REDIS_PASS'],
    'MINIO_ROOT_PASSWORD': os.environ['MINIO_PASS'],
    'PGADMIN_DEFAULT_PASSWORD': os.environ['PGADMIN_PASS'],
}

updated_lines = []
for line in lines:
    for key, value in replacements.items():
        if line.startswith(f"{key}="):
            line = f"{key}={value}"
            break
    updated_lines.append(line)

env_path.write_text("\n".join(updated_lines) + "\n")
PY

    echo "Secure passwords generated and applied to .env file"
    echo "Please review and update any values as needed"
else
    echo ".env file already exists. Skipping creation."
fi

echo "Development environment setup complete!"
