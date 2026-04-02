#!/bin/bash
set -euo pipefail

echo "==> Pulling latest from git..."
git pull

echo "==> Building React frontend..."
cd apps/web && npm ci && npm run build
cd ../..

echo "==> Starting production services..."
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build

echo "==> Running database seed..."
docker compose exec api python seed.py

DOMAIN=${DOMAIN:-"your-domain.com"}
echo ""
echo "Deploy complete."
echo "  App:  https://${DOMAIN}"
echo "  API:  https://${DOMAIN}/api/v1"
echo "  Docs: https://${DOMAIN}/api/docs"
