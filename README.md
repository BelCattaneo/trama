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
├── backend/    # FastAPI service
├── frontend/   # React + Vite UI
├── CLAUDE.md   # Project rules for the AI assistant
└── README.md
```

## Getting started

Setup instructions will land here as the project grows.

```bash
# backend
cd backend
uv run uvicorn ...

# frontend
cd frontend
npm run dev
```

## Privacy

The MVP onboards only legal entities (mutuals, cooperatives, organizations). For them, CUIT and coordinates are stored plainly — they are semi-public identifiers. Natural persons are out of the MVP scope; when they enter, identifying data is hashed and location is reduced to a zone-level geohash. Personal data is never sold to third parties and never appears in logs, public endpoints, or error responses. See [CLAUDE.md](./CLAUDE.md) for the full set of project rules.

## License

TBD.
