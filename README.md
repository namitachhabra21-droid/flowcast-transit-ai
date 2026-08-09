<div align="center">

# Flowcast

**Predictive transit intelligence — live crowd forecasting for metro and bus networks.**

[![Live Demo](https://img.shields.io/badge/demo-live-1E8E5A?style=for-the-badge)](https://flowcast-transit-ai.vercel.app)
[![Frontend](https://img.shields.io/badge/frontend-react%20%2B%20vite-61DAFB?style=flat-square)](#frontend--flowcast)
[![Backend](https://img.shields.io/badge/backend-fastapi%20%2B%20postgres-009688?style=flat-square)](#backend--transitpulse-api)
[![Auth](https://img.shields.io/badge/auth-clerk-6C47FF?style=flat-square)](#auth--multi-tenancy-design)

**[flowcast-transit-ai.vercel.app →](https://flowcast-transit-ai.vercel.app)**

<br/>

<img src="docs/screenshot.png" alt="Flowcast dashboard — live crowd map, forecasting, and AI watchlist" width="100%" />

</div>

<br/>

Flowcast visualizes metro and bus demand, forecasts crowd pressure ahead of
time, and highlights multimodal interchange risk — so commuters and
operators can see crowding coming before it happens.

This repo holds two independent pieces:

| | What it is | Status |
| --- | --- | --- |
| **[`frontend/`](frontend)** | The Flowcast dashboard — what's live at the demo link above | ✅ Deployed |
| **[`backend/`](backend)** | TransitPulse — a multi-tenant SaaS API (Postgres, Clerk auth, per-org routes/crowding) built as the eventual data layer | 🛠 Local dev only, not yet wired to the frontend |

They aren't connected yet — the deployed frontend runs on its own
representative data, and the backend is a separate, more ambitious build
documented below for anyone picking it up next.

<br/>

## Contents

- [Frontend — Flowcast](#frontend--flowcast)
- [Backend — TransitPulse API](#backend--transitpulse-api)
  - [Auth & multi-tenancy design](#auth--multi-tenancy-design)
  - [Database setup](#database-setup)
  - [Clerk setup](#clerk-setup)
  - [Running the backend](#running-the-backend)
  - [API reference](#api-v1-reference)
  - [Swappable architecture](#swappable-layers)
  - [What's deferred](#whats-deferred-named-home-not-built-yet)
- [Project structure](#project-structure)

<br/>

## Frontend — Flowcast

Live at **[flowcast-transit-ai.vercel.app](https://flowcast-transit-ai.vercel.app)**.

A single-page dashboard: live network map (metro / bus / combined), a
crowding forecast panel, route performance, operational alerts, and a
demand scenario simulator. Runs entirely on local representative data —
no backend calls.

<details>
<summary><strong>Run it locally</strong></summary>

<br/>

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5174` (pinned in `vite.config.js` to avoid
colliding with other local projects on the default Vite ports).

```bash
npm run build      # production build
npm run preview    # preview the production build locally
```

</details>

<br/>

## Backend — TransitPulse API

A multi-tenant SaaS API: each customer (a transit agency or city) is an
organization with its own routes, users, and API keys. Predicts crowding
per stop from a synthetic GTFS-style generator today, structured so a real
GTFS-RT feed and a trained model can swap in later without touching
callers. **Local dev only — no Docker, CI, or deployment config yet, and
not yet wired to the deployed frontend above.**

**Stack:** Python · FastAPI · PostgreSQL (SQLAlchemy + Alembic) · [Clerk](https://clerk.com) (email/password + Google OAuth, Organizations)

<details id="auth--multi-tenancy-design">
<summary><strong>Auth & multi-tenancy design</strong></summary>

<br/>

- **Clerk** issues sessions (email/password + Google OAuth) and owns
  Organizations. Why Clerk over Auth0/Supabase Auth: Organizations are a
  first-class primitive here (matches "each customer is a tenant" exactly),
  the React SDK is first-class, and verification is stateless (RS256 JWT
  against Clerk's JWKS) so the dashboard and API-key clients share one
  verification path. Tradeoff: vendor lock-in, per-MAU cost at scale,
  identity truth lives outside our DB.
- **Role (admin/editor/viewer) is decided by our own `org_memberships`
  table, not Clerk's role claim** — Clerk only distinguishes org:admin vs
  org:member, and custom roles are a paid tier. Keeping RBAC in our schema
  means it's ours to test and evolve independently.
- **Lazy sync, not webhooks (for now):** the first time we see a
  `(clerk_user_id, clerk_org_id)` pair on a verified session, we create the
  local `User`/`Organization`/`OrgMembership` rows on the fly (email fetched
  from Clerk's Backend API). This avoids needing a webhook receiver + tunnel
  for local dev. Production-correct version (Clerk webhooks for
  `user.created`, `organization.created`, `organizationMembership.created`)
  is a documented next step, not built here.
- **API keys are read-only by design** — resolved to the `viewer` role
  regardless of who created them, enough to call the crowding API, never
  enough to manage members/billing/keys.

</details>

<details id="database-setup">
<summary><strong>Database setup</strong></summary>

<br/>

You need a local Postgres. Two options:

**Option A — your own Postgres** (brew/postgres.app):
```bash
createdb transit_crowding
# DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/transit_crowding
```

**Option B — zero-install embedded Postgres** (no brew/Docker required —
`pgserver` is in `requirements.txt`):
```python
# one-off, from backend/ with the venv active:
python3 -c "
import pgserver
srv = pgserver.get_server('.devpgdata', cleanup_mode=None)
print(srv.get_uri())
"
```
Use the printed URI as `DATABASE_URL`. The server process it starts keeps
running independent of the Python process (`cleanup_mode=None`); re-running
the snippet just re-attaches to the same data directory.

Then, from `backend/`:
```bash
cp .env.example .env      # fill in DATABASE_URL (+ Clerk keys, see below)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head       # creates all tables
```

</details>

<details id="clerk-setup">
<summary><strong>Clerk setup</strong></summary>

<br/>

1. Create an app at [dashboard.clerk.com](https://dashboard.clerk.com).
2. Enable **Organizations** (Configure → Organizations) and **Google**
   as a social connection (Configure → SSO connections).
3. Copy the Publishable key, Secret key, and Frontend API URL into `.env`
   as `CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `CLERK_ISSUER`.
4. From a Clerk-wired frontend (not built yet — see status table above),
   users sign in and either create or join an organization; the backend
   lazily provisions matching rows on their first authenticated request.

**No Clerk account yet?** Run the dev seed script instead — it bootstraps
an org + admin user + API key directly in Postgres, bypassing Clerk, so you
can exercise the API immediately:
```bash
python -m app.scripts.seed_dev_org
```
This prints a plaintext API key and a ready-to-run `curl` command.

</details>

<details id="running-the-backend">
<summary><strong>Running the backend</strong></summary>

<br/>

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

API at `http://localhost:8000`, interactive docs at `/docs`. CORS is
enabled for `FRONTEND_ORIGIN` (default `http://localhost:3000`).

**Authenticating requests**

- **Dashboard/session:** `Authorization: Bearer <clerk_session_jwt>`
- **Programmatic/API key:** `X-API-Key: <key>`

Both resolve to an org-scoped `Principal` with a role; endpoints declare
the minimum role they need via `require_role(...)`.

</details>

<details id="api-v1-reference">
<summary><strong>API (v1) reference</strong></summary>

<br/>

| Method | Path | Min. role | Description |
| ------ | ---- | --------- | ------------ |
| GET    | `/api/v1/orgs/me`                  | viewer | Current org + your role |
| GET    | `/api/v1/members`                  | viewer | List org members |
| PATCH  | `/api/v1/members/{user_id}`        | admin  | Change a member's role |
| DELETE | `/api/v1/members/{user_id}`        | admin  | Remove a member |
| GET    | `/api/v1/api-keys`                 | admin  | List active API keys |
| POST   | `/api/v1/api-keys`                 | admin  | Create a key (plaintext shown once) |
| DELETE | `/api/v1/api-keys/{key_id}`        | admin  | Revoke a key |
| GET    | `/api/v1/routes`                   | viewer | List routes (seeds synthetic data on first call for trial orgs) |
| GET    | `/api/v1/routes/{route_id}/trips`  | viewer | Upcoming trips for a route |
| GET    | `/api/v1/trips/{trip_id}/crowding` | viewer | Predicted crowding per stop |

</details>

<details id="swappable-layers">
<summary><strong>Swappable architecture</strong></summary>

<br/>

- `app/data/synthetic_data.py` — every function takes `org_id` first. A
  real GTFS-RT ingestion module implements the same signatures (keyed off
  each org's configured feed URL, stored on `Organization.gtfs_static_url`
  / `gtfs_rt_url`) and only `app/services/transit.py`'s import changes.
- `app/ml/model.py` — `predict(org_id, route_id, stop_id, timestamp)` is
  the seam a future model registry (per-org or global, trained LightGBM,
  etc.) hooks into with the same signature.
- `app/services/transit.py` — `refresh_crowding_predictions` is written to
  become the APScheduler job body verbatim; today the API layer calls it
  synchronously per request.

</details>

<details id="whats-deferred-named-home-not-built-yet">
<summary><strong>What's deferred (named home, not built yet)</strong></summary>

<br/>

| Feature | Lands in |
| ------- | -------- |
| GTFS static/RT ingestion | `app/ingestion/` |
| Background refresh job (APScheduler, every N minutes/org) | `app/services/scheduler.py`, wraps `refresh_crowding_predictions` |
| Stripe billing, usage metering, customer portal | `app/services/billing.py`, `app/services/usage.py`, new `subscriptions`/`usage_events` tables |
| Webhook delivery (crowding-threshold alerts) | `app/services/webhooks.py`, new `webhooks` table |
| Model registry (per-org/global, LightGBM) + internal `/predict` endpoint | `app/ml/registry.py` |
| Rate limiting per plan tier | middleware in `app/main.py`, keyed off `Organization.plan_tier` |
| Wiring the deployed frontend to this API | Clerk provider + session-aware API client in `frontend/` |
| Clerk webhook sync (replacing lazy sync) | new `app/api/v1/webhooks_clerk.py` receiver |

</details>

<br/>

## Project structure

```
transit-crowding/
  frontend/                   # Flowcast — deployed dashboard (Vite, vanilla JS)
    app.js, index.html, styles.css
  backend/                   # TransitPulse — multi-tenant API (local dev only)
    app/
      main.py                 # FastAPI app factory, router mounts, CORS
      config.py                # pydantic-settings: DATABASE_URL, CLERK_*
      db/                      # declarative Base, SessionLocal, get_db
      models/                  # SQLAlchemy ORM — organizations, users,
                                # memberships, api_keys, routes, stops,
                                # trips, crowding_predictions
      schemas/                 # Pydantic request/response contracts
      auth/                    # Clerk JWT verification, API keys, RBAC
      api/v1/                  # orgs, members, api-keys, routes, trips, crowding
      data/synthetic_data.py   # org-parameterized synthetic GTFS generator
      ml/model.py              # rule-based crowding heuristic
      services/transit.py      # seeding + prediction refresh
      scripts/seed_dev_org.py  # local-only: bootstrap an org without Clerk
    alembic/                  # migrations
    requirements.txt
    .env.example
  docs/
    screenshot.png
  README.md
```

<br/>

<div align="center">

**[Open the live demo →](https://flowcast-transit-ai.vercel.app)**

</div>
