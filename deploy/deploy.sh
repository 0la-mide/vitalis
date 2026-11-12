#!/usr/bin/env bash
# Deploy VITALIS on a fresh Ubuntu VPS with Docker installed.
#   1. Point DNS for your domain at the VPS.
#   2. Copy .env.example to .env and fill it in (POSTGRES_PASSWORD, JWT_SECRET, DOMAIN, ...).
#   3. ./deploy/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Missing .env (copy .env.example)"; exit 1; }
set -a; . ./.env; set +a
: "${DOMAIN:?set DOMAIN in .env}"

sed -i.bak "s/vitalis.example.org/${DOMAIN}/g" deploy/nginx.conf && rm -f deploy/nginx.conf.bak

if [ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]; then
  echo "Getting a certificate for ${DOMAIN}…"
  sudo docker run --rm -p 80:80 -v /etc/letsencrypt:/etc/letsencrypt certbot/certbot \
    certonly --standalone -d "${DOMAIN}" --agree-tos -m "${CERTBOT_EMAIL:?set CERTBOT_EMAIL}" --non-interactive
fi

docker compose -f deploy/docker-compose.yml --env-file .env up -d --build
docker compose -f deploy/docker-compose.yml exec backend uv run --no-sync python -m app.seed
echo "Up: https://${DOMAIN}  (demo logins: docker compose exec backend cat var/DEMO_LOGINS.md)"
