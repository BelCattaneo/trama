# trama

Agroecological spreadsheet ingestion system. Producers upload weekly supply spreadsheets, consumers upload order lists, and a hybrid pipeline (deterministic + LLM) parses them, validates with a human in the loop, and persists normalized data — the plumbing for a future transport optimization layer.

This stage does not optimize routes. It is the data ingestion layer that makes future optimization possible.

## Status

Early development. No public deployment yet.

## Stack

- Backend: Python + FastAPI + PostgreSQL (via `psycopg` v3) + Pydantic, managed with [`uv`](https://docs.astral.sh/uv/)
- Frontend: React + Vite (JavaScript)

## Repository layout

```
trama/
├── backend/             # FastAPI service
├── frontend/            # React + Vite UI
├── docs/                # plan and design notes
├── docker-compose.yml   # local Postgres
├── CLAUDE.md            # project rules
└── README.md
```

## Getting started

Requirements: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), Node 20+, Docker.

```bash
cp .env.example .env

# Postgres on 127.0.0.1:5432
docker compose up -d postgres

# Backend: install deps, apply migrations, then start the server on :8000
cd backend
uv sync
uv run python -m trama.migrate up
uv run uvicorn trama.main:app --reload

# Frontend on :5173 (separate terminal)
cd frontend
npm install
npm run dev
```

A `Makefile` at the root wraps the day-to-day commands — run `make help` to see them. For a one-shot dev DB with sample data, `ENV=dev uv run python -m trama.seed_dev` inserts a producer Node so consumer flows have something to reference.

## Privacy

The MVP onboards only legal entities (mutuals, cooperatives, organizations). For them, CUIT and coordinates are stored plainly — they are semi-public identifiers. Natural persons are out of the MVP scope; when they enter, identifying data is hashed and location is reduced to a zone-level geohash. Personal data is never sold to third parties and never appears in logs, public endpoints, or error responses. See [CLAUDE.md](./CLAUDE.md) for the full set of project rules.

## License

TBD.
