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

Personal data is hashed or not stored. Location is recorded as a geohash, never as a raw coordinate. See [CLAUDE.md](./CLAUDE.md) for the full set of project rules.

## License

TBD.
