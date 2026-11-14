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
COMPOSE=(docker compose -f deploy/docker-compose.yml --env-file .env)

# Pull first, then restart this script so the rest always runs the newest version of it.
if [ -d .git ] && [ -z "${VITALIS_UPDATED:-}" ]; then
  git pull --ff-only origin main
  VITALIS_UPDATED=1 exec bash deploy/deploy.sh "$@"
fi

mkdir -p backups
if "${COMPOSE[@]}" exec -T postgres pg_isready -U vitalis -d vitalis >/dev/null 2>&1; then
  backup="backups/vitalis-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
  echo "Backing up PostgreSQL to ${backup}…"
  "${COMPOSE[@]}" exec -T postgres pg_dump -U vitalis -d vitalis | gzip > "${backup}"
fi

"${COMPOSE[@]}" up -d --build --remove-orphans

echo "Waiting for the backend (migrations run on start)…"
for _ in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" 2>/dev/null; then
    ready=1; break
  fi
  sleep 2
done
[ "${ready:-}" = 1 ] || { echo "Backend did not come up:"; "${COMPOSE[@]}" logs --tail 50 backend; exit 1; }

# nginx may still point at the old containers' addresses; reload it once the new ones are up.
"${COMPOSE[@]}" up -d --force-recreate --no-deps nginx

users=$("${COMPOSE[@]}" exec -T postgres psql -U vitalis -d vitalis -tAc "select count(*) from users" | tr -d '[:space:]')
if [ "${1:-}" = "--reset-demo" ] || [ "$users" = "0" ]; then
  echo "Seeding synthetic demo data…"
  "${COMPOSE[@]}" exec -T backend uv run --no-sync python -m app.seed
fi

# Every demo login (password, emails, demo patients' recovery codes) as a PDF next to this script's repo.
for f in DEMO_LOGINS.pdf VITALIS-User-Guide.pdf; do
  if "${COMPOSE[@]}" cp "backend:/app/var/$f" "./$f" >/dev/null 2>&1; then
    echo "Saved: $(pwd)/$f"
  fi
done

docker image prune -f >/dev/null
echo "Up: https://${DOMAIN}"
echo "Demo logins: $(pwd)/DEMO_LOGINS.pdf (run with --reset-demo once if it is missing)"
