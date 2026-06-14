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

_To be written._

## Phase 2 — User stories per epic

_To be written._

## Phase 3 — Data model

_To be written._

## Phase 4 — Build order / roadmap

_To be written._
