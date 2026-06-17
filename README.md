# trama

Agroecological spreadsheet ingestion system. Producers upload weekly supply spreadsheets, consumers upload order lists, and a hybrid pipeline (deterministic + LLM) parses them, validates with a human in the loop, and persists normalized data — the plumbing for a future transport optimization layer.

This stage does not optimize routes. It is the data ingestion layer that makes future optimization possible.

## Status

MVP functional end-to-end. No public deployment yet — runs locally against Docker Postgres.

What works today:

- **Auth**: self-service signup with CUIT validation, login, server-side sessions, bcrypt-hashed passwords, rate limiting on sensitive endpoints.
- **Upload**: xlsx, csv, jpg, png, pdf, heic. Per-format size limits, mime-type validation.
- **Hybrid parsing**: deterministic parser for xlsx/csv, Google Gemini fallback for images and PDFs.
- **Human-in-the-loop review**: every parsed document is shown side-by-side with the original for line-by-line confirmation before persisting.
- **Producer matching**: CUIT detected in the document is matched against registered nodes. Unmatched CUITs offer one-click registration of a new producer (with optional CUIT for informal nodes).
- **My orders**: dashboard of all confirmed operations with quick stats, file download, edit-supplier action.
- **Map**: Leaflet view of all registered nodes with role filtering, popups with weekly activity, and operation counts.
- **Privacy-first**: monetary values null by default, no PII in logs or error responses, see [PRIVACY.md](./PRIVACY.md).

## Stack

- **Backend**: Python 3.12 + FastAPI + PostgreSQL via [`psycopg`](https://www.psycopg.org/psycopg3/) v3 + Pydantic, managed with [`uv`](https://docs.astral.sh/uv/).
- **Frontend**: React 18 + Vite + React Router + Leaflet, plain JavaScript.
- **LLM**: Google Gemini (`gemini-2.5-flash`) for image and PDF parsing fallback.
- **Tests**: `pytest` (backend), `vitest` (frontend), Playwright (end-to-end).
- **Lint/format**: `ruff` (backend), `prettier` (frontend), GitHub Actions CI.

## Repository layout

```
trama/
├── backend/
│   ├── src/trama/         # FastAPI app, routes, parsing, LLM client
│   ├── migrations/        # versioned SQL migrations (001–008)
│   ├── seeds/             # demo data fixtures
│   ├── tests/             # pytest suite
│   └── storage/           # uploaded files (gitignored)
├── frontend/
│   ├── src/               # React app
│   │   ├── pages/         # Login, Upload, Review, MyOrders, OrderDetail, Map, Privacy, ...
│   │   ├── components/    # ProductorSelector, Layout, ...
│   │   └── contexts/      # AuthContext
│   └── e2e/               # Playwright specs
├── docs/                  # planning notes (historical)
├── docker-compose.yml     # local Postgres
├── Makefile               # day-to-day commands
├── CLAUDE.md              # project rules
├── PRIVACY.md             # data handling policy
└── README.md
```

## Getting started

Requirements: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), Node 20+, Docker.

```bash
cp .env.example .env
# Edit .env: at minimum set GOOGLE_API_KEY if you want image / PDF parsing.

make db                 # Postgres on 127.0.0.1:5432
make migrate            # apply migrations
make backend            # FastAPI on :8000

# Separate terminal:
cd frontend && npm install
make frontend           # Vite on :5173
```

Open `http://localhost:5173` and create a node. `make help` lists every target.

For demo data with a few producers already in the map: `make seed-demo`. To reset it: `make seed-demo-wipe`.

## Tests

```bash
make test               # backend pytest
make test-frontend      # frontend vitest
make test-e2e           # Playwright (requires backend + frontend running)
make lint               # ruff + prettier
```

CI runs all three suites on every PR (`.github/workflows/`).

## Privacy

The MVP onboards only legal entities (mutuals, cooperatives, organizations). For them, CUIT and coordinates are stored plainly — they are semi-public identifiers. Natural persons are out of the MVP scope; when they enter, identifying data is hashed and location is reduced to a zone-level geohash. Personal data is never sold to third parties and never appears in logs, public endpoints, or error responses. See [PRIVACY.md](./PRIVACY.md) for the full policy and [CLAUDE.md](./CLAUDE.md) for the engineering rules.

## License

TBD.
