# trama

Agroecological spreadsheet ingestion system. Producers upload **weekly supply spreadsheets**, consumers upload **order lists**, a hybrid pipeline (deterministic + LLM) parses them, validates with a human in the loop, and persists normalized data to feed a future transport optimization layer.

**This stage does NOT optimize routes.** It's the data plumbing that makes future optimization possible.

Built as an academic project with a real-world stakeholder. Treat it as something that **will be deployed** — not a throwaway notebook.

---

## Core working rules — re-read every session

These sit above every other rule.

1. **Don't assume. Don't hide confusion. Surface tradeoffs.** When you can't find what the user asked for, say so. When two interpretations are possible, present both. Substituting "close enough" data, scope, or behavior without flagging the substitution is the single most expensive failure mode. If something doesn't fit, name the gap before working around it.

2. **Minimum code that solves the problem. Nothing speculative.** No defensive code for impossible scenarios. No abstractions for a hypothetical second caller. No "while I'm here" cleanup. The change must be exactly the size of the problem.

3. **Touch only what you must. Clean up only your own mess.** Pre-existing dead code, unrelated style nits, sibling files that look refactorable — leave them alone. The diff stays scoped to the actual request. If you find a real problem outside scope, surface it; do not silently fix it.

4. **Define success criteria. Loop until verified.** Before acting, state what "done" looks like in observable terms. After acting, verify against the criteria — not against your intent. If you can't verify, say so. Do not declare success on intent alone.

---

## Stack

- **Backend**: Python + FastAPI + PostgreSQL (via `psycopg` v3) + Pydantic
- **Frontend**: React + Vite (JavaScript, no TypeScript for now)
- **Python package manager**: `uv` — **never** `pip`, `pip-tools`, `poetry`, or `conda`
- **JS package manager**: `npm`
- **Tests**: `pytest` (backend), `vitest` (frontend)
- **Lint/format**: `ruff` (backend), `prettier` (frontend)

### Before adding any dependency
**Ask for explicit confirmation.** Do not run `uv add` or `npm install <pkg>` without first stating what will be added and why. Prefer what's already installed.

---

## Language

- **Code, comments, commits, docs, READMEs, file names: English.**
- **User-facing UI text: Spanish, with inclusive `-x`**: `usuarixs`, `productorxs`, `consumidorxs`, `compañerxs`. Never the generic masculine.
- Conversation with the user happens in Spanish, but artifacts in the repo stay in English.

---

## Privacy (non-negotiable)

The MVP accepts only personas jurídicas (legal entities — mutuals, cooperatives, organizations). Privacy rules distinguish between legal entities and natural persons:

- **Legal entities** have semi-public identity and location. CUIT, latitude/longitude, and similar identifiers may be stored plainly. No hashing required.
- **Personas físicas** (out of scope for this MVP, but the constraints stand): hash or don't store identifying data. Location only at zone-level geohash.

Universal rules:

- **NEVER sell data to third parties.** Period.
- **NEVER expose personal data in logs, public endpoints, or error responses.**
- Monetary data (`amount_money`, individual prices): null by default, explicit opt-in from the collective required.
- Any new feature that touches PII requires rethinking the model before coding.

---

## Secrets (non-negotiable)

- **NEVER commit** secrets, API keys, tokens, passwords, `.env` files, or any credential file. Also restated in Commits → Hard stops.
- **NEVER print or log secrets**, even at DEBUG level. No `print(api_key)`. No `logger.debug(f"using key={key}")`. No stack traces that include credentials in their frames.
- **NEVER paste real keys** into `.env.example`, fixtures, tests, seeds, screenshots, or documentation. Use obvious placeholders (e.g. `OPENAI_API_KEY=sk-REPLACE_ME`).
- **NEVER echo `.env` contents** into chat, console output, or any visible channel — including when answering "what's in my env?".
- API responses and error messages must not contain credential values, internal URLs with embedded tokens, or stack traces against external services. Surface a generic message; log the detail server-side (without the secret).
- Frontend code must not ship server-side keys. Anything the bundle ships is public.
- If a secret leaks (committed, logged, pasted, screenshotted): **rotate it first**, then clean up the source in a separate commit / PR.

---

## UX — strong rules

- **DO NOT force normalization on the user.** The system adapts to the existing workflow: if one producer uploads a sheet with column `"verdura"` and another with `"producto"`, both work. Normalization is a backend problem.
- **Human validation before persisting LLM output.** Always a "this is what I understood — confirm/correct" loop.
- **Brutally simple uploads.** Producers with low digital literacy: photo, WhatsApp, pre-built template. If it needs a tutorial, the design is wrong.
- Error messages in human language, not stack traces.

---

## Ingestion architecture

Hybrid pipeline, **in this order**:

1. **Deterministic parser** for xlsx/csv with column mapping (most cases).
2. **Canonical product + unit dictionary** to normalize on the backend.
3. **LLM as fallback** for PDF, images, WhatsApp text, free text — not the first line.
4. **Human confirmation** before persisting.

Model entities:
- `Node` (producer / consumer / both) — with `identity_hash`, `geohash`, `geo_precision`.
- `Document` (raw uploaded file).
- `ParseAttempt` (parse attempt: strategy, confidence, JSON payload).
- `Operation` (commercial operation: weekly supply or order).
- `OperationLine` (lines: product, quantity, unit).
- `OperationDelivery` (associated deliveries).
- `Product` (with `canonical_label` and `aliases[]`).

Primary analysis unit: **weekly supply sheet (producer → buying group)** + **order list (consumer / buying group)**.

---

## Out of scope for the MVP

Do not implement, even if mentioned:
- Route optimization / VRP / solvers.
- Map with Leaflet or OSM (phase 2).
- Fine-grained multi-role auth.
- Payments, billing, full monetary module.
- Native mobile app.
- Push notifications, WhatsApp bot.

If a proposal pushes toward any of these, **discuss it explicitly before coding**.

---

## Code style

### Principles

1. **Layer correctly.** If a function is doing three things and one is a separate responsibility, factor it out. No classes for the sake of classes. No file-per-function. Find the natural boundary; put code on the right side of it.
2. **Trust validated data.** Validate at boundaries (user input, external API). Past the boundary, trust. No `try/except` for conditions that cannot occur. No `hasattr` on guaranteed attributes. No `.get(key, default)` when the caller already guarantees the key — let a `KeyError` surface the broken contract.
3. **Delete as you go.** Before declaring done, ask "what is now unused?". Delete what YOUR iteration orphaned: unused helpers, dead branches, shims without consumers. But do NOT delete pre-existing dead code.
4. **Boring syntax wins.** Multi-line `if/else` beats chained ternaries. Imports at the top (inside a function only to break a circular import, with a one-line reason). Comprehension for one transformation; a loop for two or more.
5. **Reuse before writing.** Before writing a new helper: grep the repo, check the stdlib (`itertools`, `collections`, `functools`, `pathlib`), or extend an existing util. Before a new file in a conventional directory, read **at least 3 siblings** and match the pattern.
6. **Abstract on the third real case.** Three similar functions is fine. Abstract when a fourth concrete case would benefit and the shared concept is stable. Do NOT abstract to satisfy DRY.
7. **Goldilocks**: when unsure, write the simple thing first. Add abstraction or a guard only when a concrete second case forces it.

### No defensive bloat

- No `try/except` wrapping what the boundary already validated.
- No validation of internal parameters that are already typed correctly.
- No returning `None` "just in case" — let the error surface if an assumption is broken.
- No feature flags or backwards-compatibility shims when the code can simply change.

---

## Code comments

**Default: no comment.** Add one only when the WHY is non-obvious.

- One or two lines. Prefer one.
- State the reason, not the mechanics. Good: `# Fail loud so stale envelopes do not mask fresh ones.` Bad: `# Walk the dict, check each value, skip if None, else append.`
- If the explanation needs a paragraph, put it in the commit message or PR description.
- **No tickets, PRs, or caller references in code** ("for the X flow", "used by Y endpoint"). Those belong in commits / PRs. Callers move; the comment stays.
- Describe what the function does, not who uses it.
- No multi-paragraph docstrings. One line max when needed.

---

## Commits

### Messages
- Lowercase, no colons, no `feat:`/`fix:` prefixes.
- Imperative: `add xlsx parser`, not `added` or `adding`.
- Describe the change, not the process (`add unit normalization`, not `as you asked, added…`).
- No `WIP`, `checkpoint`, `fix previous typo`, `review fix`. If "and", "also", or "+" appears in the title, that commit is two.
- **Reference the ticket**: every commit tied to an issue ends with `(#N)` so GitHub auto-links and the issue gets a backref. Example: `add backend scaffold (#1)`. If a commit covers multiple tickets, it's almost certainly two commits.
- **AI attribution**: AI involvement may be traced when it adds context, but not as automated noise. Case by case.

### Size and scope
- **One logical item per commit.** Guideline: ~200 net lines. If a commit goes past that, it's probably two.
- Long configs, docs, and instruction files can live in a single commit even if large (the 200-line guideline does not apply).
- Before committing: `git diff --cached --stat`. If the diff mixes unrelated concerns, split first.
- Deliberate staging: `git add <specific-files>` or `git add -p`. Avoid `git add .` when changes are mixed.

### Do NOT split
- Bug fix + its regression test: one commit.
- Schema change + the migration that makes it safe: one commit.
- Rename + its call-sites: one commit.

### Pre-flight before every commit
1. **Run the tests** covering the changed code. Green before committing.
2. **Let pre-commit hooks run.** Never `--no-verify` or `--no-gpg-sign`.
3. **Resolve every hook failure**, even on lines your diff did not introduce. If you commit on top of the file, those failures are yours.

If a hook blocks: diagnose, fix, stage the fix, new commit. **Do NOT** loop on `git commit --amend`.

### Hard stops
- **NEVER** commit secrets, credentials, `.env`, tokens, API keys.
- **NEVER** `git push --force` to any branch.
- **NEVER** skip hooks with flags.
- **NEVER** auto-resolve merge conflicts. Stop and show them.

---

## Deploy-aware from day 1

Even before there's a Dockerfile, **write code as if it will be deployed**:

- **Config via environment variables**, not hardcoded. `DATABASE_URL`, `OPENAI_API_KEY`, etc. in `.env` (gitignored) + `.env.example` committed.
- **No absolute local paths.** Use relative or configurable paths.
- **Structured logging** (no `print()` except for one-off debugging).
- **Healthcheck endpoint** (`GET /health`) from early on.
- **Versioned DB migrations**: sequential numbered SQL files in `backend/migrations/` (e.g. `001_init.sql`, `002_add_geohash.sql`) once the schema stops changing daily.
- **Separate file reading from request handling** (move to async processing once it grows).
- **Frontend builds to static assets** (`npm run build`) servable by any reverse proxy.

When the time comes: `docker-compose.yml` with three services — backend, frontend, and PostgreSQL with a named volume for data. Local development may start using `docker-compose up postgres` earlier than the rest, since Postgres isn't trivial to run otherwise.

---

## Workflow

- `main` is the development branch (solo project; no need for feature branches yet).
- Before structural changes (new model entity, cross-cutting refactor, new deps): **short plan in conversation before touching code.**

### Tickets are contracts — always

- Before committing work tied to a ticket: **re-read the ticket and verify every claim is true in the code**. Every line of "What", every acceptance criterion, every "Notes" item.
- Run the AC commands end-to-end (curl, ruff, npm build, etc.). "It compiles" is not "it works". "The agent reported done" is not "I verified done".
- If the implementation diverged from the ticket — extra behavior, missing behavior, renamed thing, changed scope — **update the ticket first** (`gh issue edit`), then commit. Never let code and ticket drift silently.
- Applies equally to code produced by subagents: re-check the AC yourself before commit, do not trust the agent's "done" summary at face value.

---

## How to run

_(Fill in as it gets built. Right now, repo is freshly initialized.)_

```bash
# backend
cd backend
uv run uvicorn ...

# frontend
cd frontend
npm run dev
```

