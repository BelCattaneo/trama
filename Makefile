.PHONY: help backend frontend db db-down db-logs migrate migrate-dry seed lint test test-frontend

help:
	@grep -E '^[a-z-]+:' Makefile | sed 's/:.*//'

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

lint:
	cd backend && uv run ruff check .
	cd frontend && npx prettier --check .

test:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm run test:run
