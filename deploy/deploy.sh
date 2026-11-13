#!/usr/bin/env bash
# Deploy or update VITALIS on one Ubuntu VPS with Docker.
#   First time: point DNS at the VPS, cp .env.example .env and fill it in, then ./deploy/deploy.sh
#   Every update: ./deploy/deploy.sh            (pulls, rebuilds, migrates; keeps the data)
#   Fresh demo data: ./deploy/deploy.sh --reset-demo
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Missing .env (copy .env.example)"; exit 1; }
set -a; . ./.env; set +a
: "${DOMAIN:?set DOMAIN in .env}"
COMPOSE="docker compose -f deploy/docker-compose.yml --env-file .env"

if [ -d .git ]; then
  git pull --ff-only
fi

if [ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]; then
  echo "Getting a certificate for ${DOMAIN}…"
  $COMPOSE stop nginx 2>/dev/null || true
  sudo docker run --rm -p 80:80 -v /etc/letsencrypt:/etc/letsencrypt certbot/certbot \
    certonly --standalone -d "${DOMAIN}" --agree-tos -m "${CERTBOT_EMAIL:?set CERTBOT_EMAIL}" --non-interactive
fi

$COMPOSE up -d --build --remove-orphans

echo "Waiting for the backend (migrations run on start)…"
for _ in $(seq 1 60); do
  if $COMPOSE exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" 2>/dev/null; then
    ready=1; break
  fi
  sleep 2
done
[ "${ready:-}" = 1 ] || { echo "Backend did not come up:"; $COMPOSE logs --tail 50 backend; exit 1; }

users=$($COMPOSE exec -T postgres psql -U vitalis -d vitalis -tAc "select count(*) from users" | tr -d '[:space:]')
if [ "${1:-}" = "--reset-demo" ] || [ "$users" = "0" ]; then
  echo "Seeding synthetic demo data…"
  $COMPOSE exec -T backend uv run --no-sync python -m app.seed
fi

docker image prune -f >/dev/null
echo "Up: https://${DOMAIN}  (demo logins: $COMPOSE exec backend cat var/DEMO_LOGINS.md)"
