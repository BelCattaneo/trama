.PHONY: help backend frontend db db-down db-logs lint

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

lint:
	cd backend && uv run ruff check .
	cd frontend && npx prettier --check .
