# trama — Product Plan

Living document. Sections are added as planning progresses. The repository's `CLAUDE.md` holds project rules; this file holds product scope, personas, user stories, epics, and roadmap.

---

## Phase 0 — Definition

### Problem

Agroecological collectives coordinate supply and demand among producers and consumers using heterogeneous documents (xlsx, csv, photos of paper sheets, WhatsApp messages). Cadence varies — weekly, biweekly, monthly — and product availability depends on the season. Today every document is processed by hand. No clean dataset accumulates, no historical record exists, and any future attempt to optimize transport, plan logistics, or measure throughput requires a data layer that does not exist yet.

### Long-term goal

A web tool that ingests heterogeneous documents, parses them via a hybrid pipeline (deterministic + LLM), validates the output with the human who uploaded, and persists normalized data ready to feed a future transport optimization layer.

### MVP scope

The MVP delivers **only the data ingestion layer**. No route optimization, no map, no notifications, no payments.

**In scope**

- A `Node` represents a participant. A Node can play producer, consumer, or both roles. Identity is by CUIT (unique).
- Self-service Node registration in the app.
- Basic login: email + hashed password. Server-side sessions.
- A consumer Node uploads an order list in one of three formats: **xlsx, csv, or photo** (jpg / png / pdf).
- Hybrid parsing pipeline:
  - xlsx / csv → deterministic parser with column mapping.
  - photo → LLM-based extraction.
- After parsing, the uploader sees the structured output, edits any wrong field, and confirms.
- Confirmed data persists, along with the raw document and the parse attempt(s).
- Each human correction is persisted as labelled evaluation data — used offline for parsing-quality metrics, not exposed in the app.
- The producer entity is fully modeled. No producer-upload UI in this MVP; orders may reference a pre-loaded producer Node by CUIT.

**Out of scope**

- Route / transport optimization.
- Map visualization (Leaflet, OSM).
- Producer-side upload UI.
- Multi-role auth (admin, coordinator).
- Email confirmation, password reset, magic links.
- Real-time notifications.
- Payments, billing.
- Native mobile app.
- In-app parsing-quality dashboard.

### Demo Day acceptance

A recorded video shows, end to end, without backstage edits:

1. A new Node signs up (consumer role).
2. Logs in.
3. Uploads an order list in xlsx (or csv).
4. Reviews the parsed output, edits at least one field, confirms.
5. Uploads a second order list as a photo.
6. Reviews the LLM-parsed output, edits, confirms.
7. Sees both orders in a "my orders" list.

Source on GitHub. README explains how to run locally. CLAUDE.md committed.

### Stakeholder context

Built in collaboration with a real-world agroecological collective. The primary first user during the demo is the author, representing a consumer Node within the collective. One producer Node is pre-loaded so orders can reference it.

### Privacy posture for this MVP

- CUIT only for personas jurídicas (legal entities). Treated as a semi-public identifier; not hashed in the MVP.
- Location recorded at zone level via geohash. No raw lat/lon.
- No financial information requested or stored.

---

## Phase 1 — Personas + Epics

### Personas

**P1 — Consumer Node (primary, active in MVP)**
The first user logged into the MVP. Represents a consumer-side legal entity (mutual, cooperative, or buying group) within an agroecological collective. Tech comfort medium-high: laptop user, comfortable with web apps. Operational cadence: weekly to monthly, irregular. Uploads order lists in xlsx, csv, or photo. Expects to see what the system understood before confirming.

**P2 — Producer Node (modeled, no UI flow)**
Exists as a record in the DB (Node with role `producer` or `both`). Has CUIT, display name, location. No UI flow in the MVP — no signup, no upload, no login. Pre-loaded by seed so consumer orders can reference it.

Roles explicitly out of scope for this MVP: coordinators, admins, multi-tenant operators.

### Epics

| # | Epic | Delivers |
|---|---|---|
| **E1** | Infra & data model | Postgres schema, sequential migrations, FastAPI scaffold, Vite scaffold, healthcheck, dotenv. |
| **E2** | Node registration & auth | Signup flow (Node + User), Nominatim geocoding, email + password login, server-side sessions, logout. |
| **E3** | Document upload & storage | UI to upload (xlsx/csv/photo), backend that receives, validates format, persists the original document + metadata. |
| **E4** | Deterministic parsing (xlsx/csv) | Parser that opens the spreadsheet, maps columns to canonical fields, extracts operation + lines. |
| **E5** | LLM parsing (photo) | LLM call with the image, designed prompt, extraction to the same structure as E4. |
| **E6** | Validation & confirmation | "This is what I understood" screen: parsed output, per-field editing, on confirm persists operation + lines + captures corrections as eval data. |
| **E7** | My orders | Confirmed-orders list for the logged-in Node, with detail view. |
| **E8** | Map view (post-MVP / stretch) | OSM map of all Nodes as markers, filtered by role. Not part of Demo Day acceptance. |

### Acceptance criteria per epic

Each AC answers: "what can I (the user) do once this epic is closed?" — independent of unit tests.

**E1 — Infra & data model**
- `curl http://localhost:8000/health` returns `200 OK` with `{"status":"ok","db":"ok"}`.
- Schema applied: `psql -c "\dt"` lists all model tables.
- `npm run dev` brings the UI up on `localhost:5173` with a minimal landing screen.
- `docker-compose up postgres` starts Postgres with a named volume for persistence.
- `.env.example` covers every variable the backend needs.

**E2 — Node registration & auth**
- I can sign up from the UI with CUIT + email + password + display name + role + address. Backend validates CUIT (format + checksum) and email uniqueness.
- Backend geocodes the address via Nominatim to fill `latitude` + `longitude`. If geocoding fails, I can enter lat/lon manually.
- If CUIT or email already exist, I see a clear error in Spanish.
- After signup I'm automatically logged in.
- I can log out and log back in with email + password.
- If I refresh the page while logged in, my session survives.
- If I hit `/upload` without a session, I'm redirected to `/login`.

**E3 — Document upload & storage**
- Logged in as a consumer Node, I can select an xlsx / csv / jpg / png / pdf and upload it.
- The backend rejects other formats with a readable error.
- After upload I can see the file in a "my documents" list with name, date, type, and id.
- The DB has a `Document` record with `node_id`, `mime_type`, `content_hash`, `storage_ref`, `uploaded_at`.
- Uploading the same file twice does not duplicate storage (dedup by `content_hash`).

**E4 — Deterministic parsing (xlsx/csv)**
- After uploading an xlsx fixture, a `ParseAttempt` is created with `strategy='deterministic'`, a `confidence`, and a `payload` JSON of products + quantities + units.
- The parser handles at least two column-name variants (e.g. `producto` / `item`, `cantidad` / `qty`).
- If no columns are recognizable, the parser fails cleanly: `ParseAttempt` with `confidence=0` and a message "no se pudo parsear automáticamente, pasar a revisión manual".

**E5 — LLM parsing (photo)**
- After uploading a photo of a handwritten sheet, a `ParseAttempt` is created with `strategy='llm'`, a `prompt_version`, and a `payload` JSON in the same shape as E4.
- I can see a `confidence` and reasons (e.g. "could not read line 3").
- The prompt text and version are persisted with the `ParseAttempt` so each extraction is traceable.

**E6 — Validation & confirmation**
- After uploading any format, I go to a "review" screen showing every parsed line (product, quantity, unit).
- I can edit any field. Every edit creates a `Correction` record (field, original value, corrected value, timestamp).
- I can add lines the parser missed, or delete false lines.
- On confirm, an `Operation` + its `OperationLine`s persist, marked `confirmed`. The operation is no longer editable.
- Corrections continue to live in the DB as offline evaluation data.

**E7 — My orders**
- `/my-orders` lists all my confirmed `Operation`s with date, line count, and (optionally) the referenced producer.
- Click on an operation shows the detail (lines: product, quantity, unit).
- Bonus: download the operation as CSV.

**E8 — Map view (post-MVP)**
- `/map` shows an OSM tile layer of Argentina.
- Each Node renders as a marker at its `latitude` / `longitude`.
- Markers are color-coded by `role`. Popup on click shows `display_name`, `role`, `zone_label`.
- Filter checkboxes hide/show by role. Not part of Demo Day video.

---

## Phase 2 — Tickets per epic

**All tickets live as GitHub Issues** (#1–#50), labelled by epic + stream + milestone `MVP`. E1 and E2 (#1–#17) are detailed; E3–E8 (#18–#49) are sketches that get deepened when their epic comes up; #50 is the root Makefile chore. Browse:

- All MVP issues: [`is:issue milestone:MVP`](https://github.com/BelCattaneo/trama/issues?q=is%3Aissue+milestone%3AMVP)
- E1 only: [`label:epic-1`](https://github.com/BelCattaneo/trama/issues?q=is%3Aissue+label%3Aepic-1)
- E2 only: [`label:epic-2`](https://github.com/BelCattaneo/trama/issues?q=is%3Aissue+label%3Aepic-2)
- Backend stream: [`label:stream-a`](https://github.com/BelCattaneo/trama/issues?q=is%3Aissue+label%3Astream-a)
- Frontend stream: [`label:stream-b`](https://github.com/BelCattaneo/trama/issues?q=is%3Aissue+label%3Astream-b)

**E3–E8 — sketches.** Each ticket below will be deepened (AC + Notes + deps) when the epic comes up next. Format is brief on purpose so we don't lock decisions too early.

### E3 — Document upload & storage  *(sketched)*

- **E3.1** `document` table + migration. FK to Node, `mime_type`, `content_hash` UNIQUE, `storage_ref`, `uploaded_at`. *(Stream A)*
- **E3.2** Upload endpoint `POST /api/documents`. Multipart, validates format (xlsx/csv/jpg/png/pdf) + size (≤10MB), hashes content, dedup by hash, persists. *(Stream A)*
- **E3.3** Local FS storage abstraction. Files saved under `STORAGE_PATH/<hash>`. Future-swappable for S3. *(Stream A)*
- **E3.4** List user docs endpoint `GET /api/documents`. *(Stream A)*
- **E3.5** Upload UI. Drag/drop + file picker. Client-side format/size validation. *(Stream B)*
- **E3.6** "My documents" list. Shows uploaded files, links into the review screen (E6). *(Stream B)*

### E4 — Deterministic parsing (xlsx/csv)  *(sketched)*

- **E4.1** `parse_attempt` table + migration. `document_id`, `strategy` (`'deterministic'`/`'llm'`), `confidence`, `payload` jsonb, `prompt_version` (nullable), `created_at`. *(Stream A)*
- **E4.2** Canonical `ParsePayload` Pydantic schema. Defines the shape every parser must produce: `lines: [{product, quantity, unit, raw_text?}]`. *(Stream A/C — contract)*
- **E4.3** Column-mapping config. Synonyms like `producto`/`item`, `cantidad`/`qty`, etc. mapped to canonical fields. *(Stream C)*
- **E4.4** xlsx parser. Reads with `openpyxl`, applies E4.3 mapping, outputs `ParsePayload`. *(Stream C, pure)*
- **E4.5** csv parser. Reads with stdlib `csv`, same shape as E4.4. *(Stream C, pure)*
- **E4.6** Parse orchestrator. After upload, dispatches by `mime_type`, persists `ParseAttempt`. *(Stream A — integration)*

### E5 — LLM parsing (photo)  *(sketched)*

- **E5.1** LLM provider choice + async client wrapper. **Decision pending**: Anthropic Claude / OpenAI GPT-4o / other. With retries + timeout. *(Stream A/C)*
- **E5.2** Prompt template + versioning. Prompt stored under `backend/prompts/v1_extraction.txt`. `prompt_version` persisted with every `ParseAttempt`. *(Stream A/C)*
- **E5.3** Image preprocessing. PDF → page images, resize for token limits, base64 encode. *(Stream C, pure)*
- **E5.4** LLM parse orchestrator integration. Extends E4.6 to route photo/pdf to LLM strategy. *(Stream A — integration)*
- **E5.5** Fixture-based tests. Golden-file approach with sample images + expected payloads, allowing some tolerance. *(Stream C)*

### E6 — Validation & confirmation  *(sketched)*

- **E6.1** `operation`, `operation_line`, `correction` tables + migration. Columns per `docs/plan.md` Phase 3 (to lock when we get here). *(Stream A)*
- **E6.2** Review screen. Renders parsed lines from `ParseAttempt.payload`. Inline per-field editing. *(Stream B)*
- **E6.3** Add / remove line UI. User can add lines the parser missed and delete false lines. *(Stream B)*
- **E6.4** Confirmation endpoint `POST /api/operations`. Persists `Operation` + `OperationLine`s + a `Correction` per edited field. *(Stream A)*
- **E6.5** Correction diff logic. Computes corrections between original `ParseAttempt.payload` and the user-confirmed payload. *(Stream A)*
- **E6.6** Hand-off orchestration. After parse completes → review screen; after confirm → my-orders. *(Stream A + B)*

### E7 — My orders  *(sketched)*

- **E7.1** `GET /api/operations`. Lists confirmed Operations for the logged-in Node. *(Stream A)*
- **E7.2** `GET /api/operations/:id`. Operation detail + lines. *(Stream A)*
- **E7.3** My orders list UI. *(Stream B)*
- **E7.4** Order detail UI. *(Stream B)*
- **E7.5** CSV download for an Operation. *(Stream B, bonus)*

### E8 — Map view  *(post-MVP, sketched)*

- **E8.1** `GET /api/nodes/public`. Returns Nodes with public-safe fields only (no email, no password hash). *(Stream A)*
- **E8.2** Leaflet integration. OSM standard tile layer. *(Stream B)*
- **E8.3** Marker rendering. One marker per Node at `latitude`/`longitude`. Color by role. Popup on click. *(Stream B)*
- **E8.4** Role filter UI. Show/hide producers / consumers / both. *(Stream B)*

### E1.8 — Root Makefile  *(chore)*

- **E1.8** `Makefile` at the repo root wrapping common dev commands (`backend`, `frontend`, `db`, `db-down`, `db-logs`, `lint`). Grows as later epics add targets. *(Stream A/B — root)*

### Backlog totals

| Epic | Tickets | Status |
|---|---:|---|
| E1 | 8 | Issues #1–#7, #50 |
| E2 | 10 | Issues #8–#17 |
| E3 | 6 | sketched (#18–#23) |
| E4 | 6 | sketched (#24–#29) |
| E5 | 5 | sketched (#30–#34) |
| E6 | 6 | sketched (#35–#40) |
| E7 | 5 | sketched (#41–#45) |
| E8 (post-MVP) | 4 | sketched (#46–#49) |
| **Total** | **50** | |

---

## Phase 3 — Data model

Partial. `Node` and `User` locked. Other entities defined as they're tackled.

### Entities overview

| Entity | Purpose |
|---|---|
| `Node` | Participant (consumer, producer, or both). Identified by CUIT. |
| `User` | Person who logs in. Belongs to one Node. Schema 1:N; MVP UI enforces 1:1. Stored in table `app_user` (the word `user` is reserved in PostgreSQL). |
| `Document` | Raw uploaded file (xlsx/csv/photo). Belongs to a Node. |
| `ParseAttempt` | Result of parsing a Document. Strategy = deterministic or LLM. |
| `Operation` | Confirmed commercial event (order; future: offer). Belongs to a Node. |
| `OperationLine` | Line item within an Operation (product, quantity, unit). |
| `Product` | Canonical product reference, with aliases for normalization. |
| `Correction` | Captures every human edit during validation, for offline parsing-quality analysis. |

### `Node`

```sql
Node
  id              uuid             PK, server-generated
  cuit            varchar(13)      UNIQUE, NOT NULL          -- "XX-XXXXXXXX-X"
  display_name    varchar(120)     NOT NULL
  role            varchar(20)      NOT NULL                  -- 'consumer'|'producer'|'both'
  address_text    varchar(300)     NULL
  latitude        double precision NOT NULL                  -- WGS84
  longitude       double precision NOT NULL                  -- WGS84
  zone_label      varchar(120)     NULL
  created_at      timestamptz      NOT NULL DEFAULT now()
  updated_at      timestamptz      NOT NULL DEFAULT now()

CHECK (role IN ('consumer','producer','both'))
INDEX (cuit)
INDEX (role)
```

### `User` (table: `app_user`)

The entity is `User`. The SQL table is named `app_user` because `user` is a reserved keyword in PostgreSQL; using it unquoted breaks queries and quoting it everywhere is noise. The Python / Pydantic layer keeps the name `User`.

```sql
app_user
  id              uuid             PK, server-generated
  node_id         uuid             NOT NULL REFERENCES node(id) ON DELETE RESTRICT
  email           varchar(254)     UNIQUE, NOT NULL
  password_hash   varchar(255)     NOT NULL                  -- bcrypt via passlib
  full_name       varchar(120)     NULL
  last_login_at   timestamptz      NULL
  created_at      timestamptz      NOT NULL DEFAULT now()
  updated_at      timestamptz      NOT NULL DEFAULT now()

INDEX (node_id)
INDEX (email)
```

### `Document`

Raw uploaded file. Belongs to a Node. Same bytes shared via storage-layer dedup; multiple `Document` rows can point at the same `storage_ref`.

```sql
document
  id                uuid             PK, server-generated
  node_id           uuid             NOT NULL REFERENCES node(id) ON DELETE CASCADE
  original_filename varchar(255)     NOT NULL
  mime_type         varchar(100)     NOT NULL                 -- CHECK whitelisted to 5 formats
  size_bytes        integer          NOT NULL CHECK > 0
  content_hash      char(64)         NOT NULL                 -- SHA-256 hex, NOT UNIQUE
  storage_ref       varchar(500)     NOT NULL                 -- opaque ref returned by the storage layer
  uploaded_at       timestamptz      NOT NULL DEFAULT now()

CHECK (mime_type IN (xlsx, csv, jpeg, png, pdf — full mime strings))
INDEX (node_id)
INDEX (content_hash)
```

### Notes

- CUIT validation = format (`XX-XXXXXXXX-X`) + checksum (Argentina). Verified at signup.
- `password_hash` uses bcrypt via `passlib` (dependency to be added when E2 starts).
- MVP UI enforces 1 User per Node; schema allows N for future multi-user.
- No `is_active` / soft-delete in MVP. Real deletion is not exposed in the UI.
- Privacy: for the MVP, all Nodes are personas jurídicas, so lat/lon is stored plainly (see CLAUDE.md).
- Address geocoding via Nominatim (no API key required, sent with a proper User-Agent).
- Index notation above (`INDEX (cuit)`, `INDEX (email)`) means "this column needs a lookup path"; UNIQUE constraints already create such an index, so the migration only emits explicit `CREATE INDEX` statements for non-unique columns (`role`, `node_id`).
- `Document.content_hash` is **NOT UNIQUE** — two rows with the same hash are allowed (different upload context). The storage layer dedupes the physical bytes; two rows can share the same `storage_ref`.
- `Document.mime_type` whitelisted via CHECK constraint: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `text/csv`, `image/jpeg`, `image/png`, `application/pdf`. Backend re-detects mime from bytes before insert; the constraint is defense-in-depth.
- `Document.node_id` cascades on delete; if a Node disappears, its documents go too.

### `ParseAttempt`

Result of one attempt to parse a `Document`. Many rows per document — one per strategy tried (deterministic, llm). Failed attempts persist with `error_message` and `confidence=0` for debug and re-parse.

```sql
parse_attempt
  id              uuid             PK, server-generated
  document_id     uuid             NOT NULL REFERENCES document(id) ON DELETE CASCADE
  strategy        varchar(20)      NOT NULL                 -- CHECK ('deterministic', 'llm')
  confidence      real             NULL                     -- CHECK 0..1 or NULL
  payload         jsonb            NULL                     -- ParsePayload validated; NULL when failed
  prompt_version  varchar(40)      NULL                     -- only for strategy='llm'
  error_message   text             NULL                     -- set when payload is NULL
  is_winner       boolean          NOT NULL DEFAULT FALSE   -- set by E6 review confirmation
  created_at      timestamptz      NOT NULL DEFAULT now()

INDEX (document_id)
UNIQUE INDEX (document_id) WHERE is_winner   -- at most one winner per document
```

### `Operation`

Confirmed commercial event. One row per parse_attempt promoted by the human reviewer to a persisted operation. Belongs to a Node (the producer or consumer that owns the source document).

```sql
operation
  id                uuid             PK, server-generated
  node_id           uuid             NOT NULL REFERENCES node(id) ON DELETE RESTRICT
  parse_attempt_id  uuid             NOT NULL REFERENCES parse_attempt(id) ON DELETE RESTRICT
  kind              varchar(20)      NOT NULL                 -- CHECK ('order', 'offer')
  operation_date    date             NOT NULL
  status            varchar(20)      NOT NULL                 -- CHECK ('confirmed')
  confirmed_at      timestamptz      NOT NULL
  created_at        timestamptz      NOT NULL DEFAULT now()
  supplier_node_id  uuid             NULL REFERENCES node(id) ON DELETE SET NULL

UNIQUE (parse_attempt_id)
INDEX (node_id, confirmed_at DESC)
INDEX (supplier_node_id)
```

`supplier_node_id` uses ON DELETE SET NULL so that deregistering a supplier preserves historical operations (with a null pointer) rather than dropping them.

### `OperationLine`

Line item within an Operation. Cascades when the parent operation is deleted.

```sql
operation_line
  id            uuid             PK, server-generated
  operation_id  uuid             NOT NULL REFERENCES operation(id) ON DELETE CASCADE
  product       varchar(200)     NOT NULL
  quantity      numeric(12,3)    NOT NULL CHECK > 0
  unit          varchar(40)      NULL
  raw_text      text             NULL
  line_no       smallint         NOT NULL
  page          smallint         NULL

INDEX (operation_id)
```

### `Correction`

Captures every human edit applied during validation against the original `ParsePayload`. Used offline to measure parsing quality; never read by the runtime parser. Cascades when the parent parse_attempt is deleted.

```sql
correction
  id                uuid             PK, server-generated
  parse_attempt_id  uuid             NOT NULL REFERENCES parse_attempt(id) ON DELETE CASCADE
  line_no           smallint         NULL                     -- index into original payload; NULL for 'line_added'
  field             varchar(40)      NOT NULL                 -- CHECK ('product','quantity','unit','line_added','line_removed')
  original_value    text             NULL
  corrected_value   text             NULL
  created_at        timestamptz      NOT NULL DEFAULT now()

INDEX (parse_attempt_id)
```

### Notes (operations)

- `Operation.node_id` and `Operation.parse_attempt_id` use `ON DELETE RESTRICT` because a confirmed operation is the system of record; deleting the source document or its parse attempts must not silently drop the persisted operation.
- `Operation.parse_attempt_id` is `UNIQUE`: at most one operation per parse attempt. The "winner" parse attempt produces the operation; re-confirmation re-uses the same row instead of creating a duplicate.
- `Operation.status` is constrained to `'confirmed'` for the MVP; `draft` / `cancelled` will be added when the lifecycle grows.
- `Operation.kind` accepts `'order'` (consumer demand) and `'offer'` (producer supply). The MVP exercises `order` first.
- `OperationLine.quantity` uses `numeric(12,3)` to keep three decimals (e.g. `0.250 kg`) without floating-point drift.
- `Correction.field='line_added'` carries `line_no=NULL` because the corrected line did not exist in the original payload; `corrected_value` stores the new line as JSON.
- `Correction.field='line_removed'` carries the original line in `original_value` (JSON) and `corrected_value=NULL`.

### Pending entities

`Product`, `term_alias`. Defined in the next iteration.

---

## Phase 4 — Build order + parallelization

### Sequential view (single-threaded)

Tentative order if built one epic at a time: E1 → E2 → E3 → E4 → E6 → E5 → E7 → (E8 post-MVP).

### Parallel streams

Once the data contracts and schemas are locked (end of E1), three streams can move in parallel:

- **Stream A — Backend service**
  Endpoints, persistence, session, integrations. Implements E2 backend, E3 backend, E6 backend, E7 backend.

- **Stream B — Frontend**
  Vite app, routing, forms, screens. Implements E2 frontend, E3 frontend, E6 frontend, E7 frontend. Can work against a mocked backend until A is ready to integrate.

- **Stream C — Parsing libraries**
  Pure functions: file in, structured JSON out. Implements E4 (deterministic) and E5 (LLM). Plays nice with fixtures and no HTTP. Wired into the backend at integration time.

### Integration points

The streams must converge on shared contracts agreed upfront:
- Pydantic schemas for `ParsePayload`, `OperationDraft`, `OperationConfirmed`.
- HTTP API contract for `/documents`, `/parse-attempts`, `/operations`, `/auth/*`.
- Frontend uses the same Pydantic-derived JSON shapes (mirrored as TS/JS types if helpful).

Once contracts are pinned, streams A, B, and C can progress with minimal blocking. Integration tickets at the end of each epic wire them together.
