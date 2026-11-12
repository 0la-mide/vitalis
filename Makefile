.PHONY: setup db migrate seed demo-reset dev backend model frontend test lint types build overdue-now logins

BACKEND := cd backend &&
FRONTEND := cd frontend &&

setup: ## Install deps, create local DBs, migrate, seed
	$(BACKEND) uv sync
	$(FRONTEND) npm install
	$(MAKE) db migrate seed

db: ## Create local Postgres role + databases (native dev, no Docker)
	psql -h localhost -d postgres -tc "SELECT 1 FROM pg_roles WHERE rolname='vitalis'" | grep -q 1 || \
	  psql -h localhost -d postgres -c "CREATE ROLE vitalis LOGIN PASSWORD 'vitalis_dev' CREATEDB"
	psql -h localhost -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='vitalis'" | grep -q 1 || createdb -h localhost -O vitalis vitalis
	psql -h localhost -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='vitalis_test'" | grep -q 1 || createdb -h localhost -O vitalis vitalis_test

migrate:
	$(BACKEND) uv run alembic upgrade head
	$(BACKEND) ALEMBIC_DATABASE_URL=postgresql+asyncpg://vitalis:vitalis_dev@localhost:5432/vitalis_test uv run alembic upgrade head

seed demo-reset: ## Wipe and reseed synthetic demo data (seconds). Logins -> backend/var/DEMO_LOGINS.md
	$(BACKEND) uv run python -m app.seed

backend:
	$(BACKEND) uv run uvicorn app.main:app --port 8000 --reload

model:
	$(BACKEND) uv run uvicorn --app-dir ../model app:app --port 8100

frontend:
	$(FRONTEND) npm run dev

dev: ## Run model, backend and frontend together (Ctrl-C stops all)
	@trap 'kill 0' INT TERM; \
	$(MAKE) model & $(MAKE) backend & $(MAKE) frontend & wait

test:
	$(BACKEND) uv run pytest -q

lint:
	$(BACKEND) uv run ruff check app tests
	$(FRONTEND) npm run lint && npm run typecheck

types: ## Regenerate frontend API types from FastAPI's OpenAPI
	$(BACKEND) PYTHONPATH=. uv run python scripts/export_openapi.py > ../frontend/types/openapi.json
	$(FRONTEND) npm run types

build:
	$(FRONTEND) npm run build

overdue-now: ## Testing only: make every accepted referral look 3 h old; the overdue job flags it within a minute
	PGPASSWORD=vitalis_dev psql -h localhost -U vitalis -d vitalis -c "UPDATE referrals SET accepted_at = now() - interval '3 hours' WHERE status = 'accepted'"

logins: ## Show the demo accounts (password included; local only)
	@cat backend/var/DEMO_LOGINS.md
