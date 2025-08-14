#!/usr/bin/env bash
set -e
npm ci || npm install
npm -ws run build || true
echo "Scaffold ready. Start a service: npm run dev -w services/auth-svc"
