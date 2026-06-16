.PHONY: help backend frontend db db-down db-logs migrate migrate-dry seed seed-demo seed-demo-dry seed-demo-wipe lint test test-frontend test-e2e test-e2e-headed test-e2e-ui

help:
	@grep -E '^[a-z0-9-]+:' Makefile | sed 's/:.*//'

backend:
	cd backend && uv run uvicorn trama.main:app --reload

frontend:
	cd frontend && npm run dev

db:
	docker compose up -d postgres

db-down:
	docker compose down

db-logs:
	docker compose logs -f postgres

migrate:
	cd backend && uv run python -m trama.migrate up

migrate-dry:
	cd backend && uv run python -m trama.migrate up --dry-run

seed:
	cd backend && ENV=dev uv run python -m trama.seed_dev

seed-demo:
	cd backend && uv run python -m trama.seed_demo

seed-demo-dry:
	cd backend && uv run python -m trama.seed_demo --dry-run

seed-demo-wipe:
	cd backend && uv run python -m trama.seed_demo --wipe

lint:
	cd backend && uv run ruff check .
	cd frontend && npx prettier --check .

test:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm run test:run

test-e2e:
	cd frontend && npm run test:e2e

test-e2e-headed:
	cd frontend && npm run test:e2e:headed

test-e2e-ui:
	cd frontend && npm run test:e2e:ui
