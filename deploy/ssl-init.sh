#!/bin/bash
# Run ONCE to get initial Let's Encrypt certificate.
# Usage: ./deploy/ssl-init.sh yourdomain.com admin@yourdomain.com
set -euo pipefail

DOMAIN=${1:?Usage: $0 DOMAIN EMAIL}
EMAIL=${2:?Usage: $0 DOMAIN EMAIL}

echo "==> Creating required directories..."
mkdir -p ./deploy/certbot/conf ./deploy/certbot/www

echo "==> Starting nginx with HTTP-only config for ACME challenge..."
docker compose up -d nginx

echo "==> Waiting for nginx to be ready..."
sleep 3

echo "==> Requesting Let's Encrypt certificate for ${DOMAIN}..."
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email "${EMAIL}" \
  --agree-tos \
  --no-eff-email \
  -d "${DOMAIN}"

echo "==> Reloading nginx with SSL config..."
docker compose exec nginx nginx -s reload

echo ""
echo "SSL certificate obtained successfully."
echo "Domain:  https://${DOMAIN}"
echo "Certs:   ./deploy/certbot/conf/live/${DOMAIN}/"
echo ""
echo "Next: run ./deploy/deploy.sh to complete the deployment."
