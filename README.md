# TransitPulse — Predictive Public Transit Crowding

A multi-tenant SaaS product predicting how crowded upcoming transit trips
will be, per stop. Each customer (a transit agency or city) is an
organization with its own routes, users, and API keys. Local dev only —
no Docker, CI, or deployment config yet.

## Stack

- **Backend:** Python, FastAPI, PostgreSQL (SQLAlchemy + Alembic)
- **Auth:** [Clerk](https://clerk.com) — email/password + Google OAuth, Organizations for multi-tenancy
- **Frontend:** React (Vite)

## Status: what's built vs. what's next

This pass implemented the **database schema and auth layer** — the
foundation everything else depends on — plus a thin vertical slice (org
info, API keys, members, routes/trips/crowding) proving the whole stack
works end-to-end against real Postgres. **Not yet built:** GTFS ingestion,
the APScheduler refresh job, Stripe billing, webhook delivery, the model
registry, rate limiting, and the marketing/dashboard frontend split. See
"What's deferred" below for where each lands.

**The existing frontend (`frontend/`) still targets the old unauthenticated
endpoints and will not work against this backend as-is** — wiring it to
Clerk and `/api/v1/...` is the next piece of work, not done in this pass.

## Project structure

```
transit-crowding/
  backend/
    app/
      main.py                 # FastAPI app factory, router mounts, CORS
      config.py                # pydantic-settings: DATABASE_URL, CLERK_*
      db/
        base.py                 # declarative Base
        session.py               # engine, SessionLocal, get_db dependency
      models/                  # SQLAlchemy ORM — the system of record
        organization.py, user.py, membership.py, api_key.py,
        route.py, stop.py, trip.py, crowding_prediction.py
      schemas/                 # Pydantic request/response contracts
      auth/
        clerk.py                 # JWKS fetch + session JWT verification
        api_key.py                # key generation/hashing/verification
        dependencies.py          # get_current_principal, require_role, org scoping
      api/v1/
        router.py, orgs.py, api_keys.py, members.py,
        routes.py, trips.py, crowding.py
      data/
        synthetic_data.py        # org-parameterized synthetic GTFS-style generator
      ml/
        model.py                  # rule-based crowding heuristic
      services/
        transit.py                # seeding + prediction refresh (today: on-demand; tomorrow: scheduler job body)
      scripts/
        seed_dev_org.py           # local-only: bootstrap an org+admin without a live Clerk account
    alembic/                    # migrations
    requirements.txt
    .env.example
  frontend/                   # existing demo UI — not yet wired to auth/v1 API (see Status)
  README.md
```

## Auth & multi-tenancy design

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

## Database setup

You need a local Postgres. Two options:

**Option A — your own Postgres** (brew/postgres.app):
```bash
createdb transit_crowding
# DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/transit_crowding
```

**Option B — zero-install embedded Postgres** (what this was built/tested
against here, no brew/Docker required — `pgserver` is in requirements.txt):
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

## Clerk setup

1. Create an app at [dashboard.clerk.com](https://dashboard.clerk.com).
2. Enable **Organizations** (Configure → Organizations) and **Google**
   as a social connection (Configure → SSO connections).
3. Copy the Publishable key, Secret key, and Frontend API URL into `.env`
   as `CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `CLERK_ISSUER`.
4. From the frontend (once wired up), users sign in and either create or
   join an organization — the backend lazily provisions matching rows on
   their first authenticated request.

**No Clerk account yet?** Run the dev seed script instead — it bootstraps
an org + admin user + API key directly in Postgres, bypassing Clerk, so you
can exercise the API immediately:
```bash
python -m app.scripts.seed_dev_org
```
This prints a plaintext API key and a ready-to-run `curl` command.

## Running the backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

API at `http://localhost:8000`, interactive docs at `/docs`. CORS is
enabled for `FRONTEND_ORIGIN` (default `http://localhost:3000`).

### Authenticating requests

- **Dashboard/session:** `Authorization: Bearer <clerk_session_jwt>`
- **Programmatic/API key:** `X-API-Key: <key>`

Both resolve to an org-scoped `Principal` with a role; endpoints declare
the minimum role they need via `require_role(...)`.

### API (v1)

| Method | Path                                  | Min. role | Description |
| ------ | -------------------------------------- | --------- | ------------ |
| GET    | `/api/v1/orgs/me`                      | viewer    | Current org + your role |
| GET    | `/api/v1/members`                      | viewer    | List org members |
| PATCH  | `/api/v1/members/{user_id}`            | admin     | Change a member's role |
| DELETE | `/api/v1/members/{user_id}`            | admin     | Remove a member |
| GET    | `/api/v1/api-keys`                     | admin     | List active API keys |
| POST   | `/api/v1/api-keys`                     | admin     | Create a key (plaintext shown once) |
| DELETE | `/api/v1/api-keys/{key_id}`            | admin     | Revoke a key |
| GET    | `/api/v1/routes`                       | viewer    | List routes (seeds synthetic data on first call for trial orgs) |
| GET    | `/api/v1/routes/{route_id}/trips`      | viewer    | Upcoming trips for a route |
| GET    | `/api/v1/trips/{trip_id}/crowding`     | viewer    | Predicted crowding per stop |

## Swappable layers (kept from the original demo, now org-aware)

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

## What's deferred (named home, not built yet)

| Feature | Lands in |
| ------- | -------- |
| GTFS static/RT ingestion | `app/ingestion/` |
| Background refresh job (APScheduler, every N minutes/org) | `app/services/scheduler.py`, wraps `refresh_crowding_predictions` |
| Stripe billing, usage metering, customer portal | `app/services/billing.py`, `app/services/usage.py`, new `subscriptions`/`usage_events` tables |
| Webhook delivery (crowding-threshold alerts) | `app/services/webhooks.py`, new `webhooks` table |
| Model registry (per-org/global, LightGBM) + internal `/predict` endpoint | `app/ml/registry.py` |
| Rate limiting per plan tier | middleware in `app/main.py`, keyed off `Organization.plan_tier` |
| Marketing site + authenticated dashboard split | `frontend/marketing/`, `frontend/app/` (Clerk-wrapped) |
| Clerk webhook sync (replacing lazy sync) | new `app/api/v1/webhooks_clerk.py` receiver |

## Frontend

Unchanged from the original demo for now — see `frontend/README` usage in
the previous version of this doc. **It targets the old unauthenticated
endpoints and needs to be rewired** (Clerk provider, session-aware
`api.js`, dashboard shell) before it will work against this backend.
