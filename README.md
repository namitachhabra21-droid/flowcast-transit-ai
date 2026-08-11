<div align="center">

# Flowcast

**Predictive transit intelligence — live crowd forecasting for metro and bus networks.**

[![Live Demo](https://img.shields.io/badge/demo-live-1E8E5A?style=for-the-badge)](https://flowcast-transit-ai.vercel.app)
[![Frontend](https://img.shields.io/badge/frontend-react%20%2B%20typescript-61DAFB?style=flat-square)](#frontend--flowcast)
[![Backend](https://img.shields.io/badge/backend-fastapi-009688?style=flat-square)](#backend--transitpulse-api)
[![ML](https://img.shields.io/badge/ML-random%20forest-F7931E?style=flat-square)](#the-prediction-model)
[![Deployed on Render](https://img.shields.io/badge/API-render-46E3B7?style=flat-square)](https://transit-crowding-backend.onrender.com/docs)
[![Auth](https://img.shields.io/badge/auth-clerk-6C47FF?style=flat-square)](#auth--multi-tenancy-design)

**[flowcast-transit-ai.vercel.app →](https://flowcast-transit-ai.vercel.app)**

<br/>

<img src="docs/screenshot-network.png" alt="Flowcast — AI journey planner and live crowd map" width="100%" />

</div>

<br/>

Flowcast visualizes metro and bus demand, forecasts crowd pressure ahead of
time, and recommends the least-crowded route between any two stations — so
commuters see crowding coming before it happens, and operators can act on it.

The dashboard is a live React app talking to a real FastAPI service in
production: pick a source and destination, and the **AI Journey Planner**
calls a trained Random Forest model to compare every viable route by
predicted occupancy, refreshing every 5 seconds. The model is real — trained
on ~104k rows of real transit ridership — not a mocked response; see
[The prediction model](#the-prediction-model) for what it actually does and
where it's still limited.

<br/>

## Contents

- [How it's wired](#how-its-wired)
- [Features](#features)
- [Frontend — Flowcast](#frontend--flowcast)
- [Backend — TransitPulse API](#backend--transitpulse-api)
  - [The prediction model](#the-prediction-model)
  - [Auth & multi-tenancy design](#auth--multi-tenancy-design)
  - [Database setup](#database-setup)
  - [Clerk setup](#clerk-setup)
  - [Running the backend](#running-the-backend)
  - [API reference](#api-reference)
  - [Swappable architecture](#swappable-layers)
  - [What's deferred](#whats-deferred-named-home-not-built-yet)
- [Project structure](#project-structure)

<br/>

## How it's wired

```
  Flowcast (Vercel)                                    TransitPulse API (Render)
  flowcast-transit-ai.vercel.app                        transit-crowding-backend.onrender.com

              GET /stations, POST /recommend-route
        ───────────────────────────────────────────▶
                                                          predict_best_effort() →
                                                          trained Random Forest,
                                                          falls back to a heuristic
              ◀───────────────────────────────────────
                    polled every 5s while the
                       Journey Planner is open
```

| | What it is | Status |
| --- | --- | --- |
| **[`frontend/`](frontend)** | The Flowcast dashboard | ✅ Live on Vercel |
| **[`backend/`](backend)** — `/predict`, `/recommend-route`, `/stations` | The crowding model the Journey Planner calls | ✅ Live on Render, connected to the frontend |
| **[`backend/`](backend)** — `/api/v1/*` | A separate multi-tenant SaaS layer (Postgres, Clerk auth, per-org routes) built as the eventual data layer for the org-scoped product | 🛠 Runs locally against a real Postgres; not linked to a production database yet |

<br/>

## Features

- **AI Journey Planner** — pick a source and destination, get every viable
  route (direct + single-transfer) ranked by predicted occupancy from a
  trained Random Forest model, with a plain-language reason for the
  recommendation and a confidence score. Re-runs automatically whenever you
  change either station or hit swap, and polls the live API every 5 seconds
  while open.
- **Live crowd map** — a network digital twin showing real-time station load
  across metro, bus, or both, with a time scrubber to scan recent history.
- **Crowd Forecast Studio** — a clickable per-line heatmap (select a cell for
  its route/time/predicted-load breakdown) projecting demand up to 2 hours
  ahead, plus the next predicted network peak — hottest line, busiest
  station, expected riders — all derived live from the heatmap itself, not
  hardcoded. "Run latest model" genuinely regenerates it.
- **Alerts & interventions** — capacity-breach predictions with a
  recommended response (deploy marshals, hold trains, issue an advisory).
- **Demand simulator** — stress-test the network against a hypothetical
  event (attendance, proximity, affected corridors) before it happens.

<br/>

## Frontend — Flowcast

Live at **[flowcast-transit-ai.vercel.app](https://flowcast-transit-ai.vercel.app)**.

React 18 + TypeScript on Vite. The Journey Planner and station list talk to
the live FastAPI backend; everything else (the map, forecast heatmap,
alerts, simulator) runs on local representative data that updates on a
timer, so the dashboard feels alive even without a live GTFS feed behind it.

<details>
<summary><strong>Run it locally</strong></summary>

<br/>

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5174` (pinned in `vite.config.ts` to avoid
colliding with other local projects on the default Vite ports). Talks to
`http://localhost:8000` automatically when running on localhost — see
[Running the backend](#running-the-backend) to stand that up too, or leave
it be and the planner falls back to a local demo prediction.

```bash
npm run build      # production build
npm run preview    # preview the production build locally
npm run typecheck  # tsc --noEmit
```

</details>

<br/>

## Backend — TransitPulse API

Live at **[transit-crowding-backend.onrender.com](https://transit-crowding-backend.onrender.com)** ([interactive docs](https://transit-crowding-backend.onrender.com/docs)).

Two things live in this one service:

1. **The crowding model** (`/predict`, `/recommend-route`, `/stations`) —
   unauthenticated, root-mounted, and what the deployed frontend actually
   calls. This is the part that's live end-to-end.
2. **TransitPulse**, a multi-tenant SaaS API under `/api/v1` — each customer
   (a transit agency or city) is an organization with its own routes, users,
   and API keys, predicting crowding per stop from a synthetic GTFS-style
   generator. Structured so a real GTFS-RT feed and a trained model can swap
   in later without touching callers. Runs locally against a real Postgres;
   **not yet linked to a production database**, so it isn't reachable from
   the deployed frontend.

**Stack:** Python · FastAPI · PostgreSQL (SQLAlchemy + Alembic) · [Clerk](https://clerk.com) (email/password + Google OAuth, Organizations) · deployed on [Render](https://render.com)

<details id="the-prediction-model">
<summary><strong>The prediction model</strong></summary>

<br/>

`predict_best_effort()` (`app/api/predict.py`) is the one entry point every
caller uses — `/predict` directly, and `/recommend-route` once per candidate
route. It tries the trained model first and falls back to a heuristic on any
failure, so a bad request or a cold artifact never breaks a caller, it just
degrades.

**The trained model** (`app/ml/inference.py`, `model_version:
"flowcast-random-forest-v1"`) is a real `RandomForestRegressor` trained on
~104k rows of real NYC subway ridership (`app/data/flowcast_mta_data.csv`,
128,803 hourly readings across 428 stations — see
`app/ml/artifacts/model_metadata.json` for the full training spec). It's not
a mocked response.

Two things worth knowing about it:

- **Pruned from 300 trees to 20.** The full forest needs ~700MB just to
  unpickle — more than Render's free-tier 512MB cap, before the app's other
  dependencies (pandas/numpy/scikit-learn/FastAPI) even load. A forest's
  prediction is the mean of its trees' outputs, so keeping a subset is
  standard model compression, not a fake model — verified empirically (not
  guessed) that the pruned model measures ~295MB RSS importing the full app,
  with predictions shifting only ~2% vs. the untouched 300-tree version on
  the stations it was actually trained on.
- **Delhi's 9 stations are real geographic entries, not a borrowed NYC
  identity, but the model has never seen Delhi ridership.** The station
  mapping/metadata were originally NYC-only; this app's stations were
  appended with their real public lat/long so the model can look them up and
  actually run, instead of always falling back. But it was trained
  exclusively on NYC data, so for Delhi stations it's extrapolating on
  real-but-out-of-distribution input — geographic features carry little
  signal that far outside the training range, so predictions currently vary
  mostly by time-of-day and input ridership, not station. Treat trained-model
  output for Delhi stations as illustrative, not a validated forecast, until
  it's retrained on real Delhi ridership data.

Lag/rolling-window features (`ridership_lag_1h`, `rolling_mean_6h`, etc.) are
looked up from the historical dataset via nearest-neighbor search
(`_nearest_reading`, within a 45-day window) rather than requiring an exact
timestamp match — the dataset is sparse (some stations have only a few
hundred readings across a full year), and this app always predicts for
*right now*, which never exists verbatim in a 2021–2022 dataset. Falls back
to the request's `current_passenger_count` when nothing is close enough,
which is always the case for the 9 Delhi stations.

**The heuristic fallback** (`predict_crowding()`, `model_version:
"crowdnet-gbrt-v2.4.1"`) is what actually serves a request whenever the
trained model can't — an unrecognized station, missing artifacts, whatever.
What it returns alongside the point estimate:

- **Per-factor contributions** — e.g. `rush_hour_peak: +30%`,
  `weekend_or_holiday_damping: -30%`, `live_ridership_signal: ±8%` — so a
  prediction comes with a reason, not just a number.
- **A confidence score** that dips near the LOW/MEDIUM/HIGH decision
  boundaries (40%, 75%), the same intuition as margin-based confidence on a
  real classifier.
- **A live ridership signal** — current load is shaped by an actual
  rush-hour curve against the real clock, plus a short-period,
  deterministic-per-time-bucket drift term. Poll the same route twice a few
  seconds apart and the numbers genuinely move, the way a feed backed by
  live sensors would.
- **Measured `inference_time_ms`** — wall-clock time around the actual
  prediction call, not a fake number.

</details>

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
`pgserver` is in `requirements-dev.txt`, kept out of `requirements.txt` since
it has no prebuilt wheel for every deploy platform):
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
pip install -r requirements.txt -r requirements-dev.txt   # drop the second file if using Option A
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
4. From a Clerk-wired frontend (not built yet — this is for the separate
   `/api/v1` SaaS layer, see status table above), users sign in and either
   create or join an organization; the backend lazily provisions matching
   rows on their first authenticated request.

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
enabled for `FRONTEND_ORIGIN` plus `EXTRA_CORS_ORIGINS` (the deployed
Vercel origin is allowed by default).

**Authenticating requests**

- `/predict`, `/recommend-route`, `/stations` — unauthenticated, called
  directly by the frontend.
- **`/api/v1/*` — Dashboard/session:** `Authorization: Bearer <clerk_session_jwt>`
- **`/api/v1/*` — Programmatic/API key:** `X-API-Key: <key>`

Both auth paths resolve to an org-scoped `Principal` with a role;
`/api/v1` endpoints declare the minimum role they need via `require_role(...)`.

</details>

<details id="api-reference">
<summary><strong>API reference</strong></summary>

<br/>

**Crowding model — live in production, unauthenticated**

| Method | Path | Description |
| ------ | ---- | ------------ |
| GET    | `/health`          | Liveness check |
| GET    | `/stations`        | All stations + line membership, powers the planner's From/To selects |
| POST   | `/predict`         | Crowding prediction for one route/station/timestamp — see [The prediction model](#the-prediction-model) |
| POST   | `/recommend-route`  | Given `source_station` + `destination_station`, evaluates every viable route and recommends one |

**TransitPulse SaaS layer — local dev only (see [status table](#how-its-wired))**

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

- `app/ml/inference.py` — `predict_ridership(station_id, timestamp,
  current_passenger_count)` is the seam a retrained model hooks into.
  Retraining on real Delhi ridership data (instead of the current NYC-only
  model extrapolating on Delhi's lat/long) is the highest-value next step
  here — see [The prediction model](#the-prediction-model).
- `app/data/synthetic_data.py` (TransitPulse/`/api/v1` layer) — every
  function takes `org_id` first. A real GTFS-RT ingestion module implements
  the same signatures (keyed off each org's configured feed URL, stored on
  `Organization.gtfs_static_url` / `gtfs_rt_url`) and only
  `app/services/transit.py`'s import changes.
- `app/services/transit.py` — `refresh_crowding_predictions` is written to
  become the APScheduler job body verbatim; today the API layer calls it
  synchronously per request.

</details>

<details id="whats-deferred-named-home-not-built-yet">
<summary><strong>What's deferred (named home, not built yet)</strong></summary>

<br/>

| Feature | Lands in |
| ------- | -------- |
| Production database for the `/api/v1` SaaS layer | Render Postgres is already provisioned — wire `DATABASE_URL` on the backend service |
| GTFS static/RT ingestion | `app/ingestion/` |
| Background refresh job (APScheduler, every N minutes/org) | `app/services/scheduler.py`, wraps `refresh_crowding_predictions` |
| Stripe billing, usage metering, customer portal | `app/services/billing.py`, `app/services/usage.py`, new `subscriptions`/`usage_events` tables |
| Webhook delivery (crowding-threshold alerts) | `app/services/webhooks.py`, new `webhooks` table |
| Retrain the Random Forest on real Delhi ridership data | `app/ml/inference.py` — same `predict_ridership()` signature, new artifacts |
| Rate limiting per plan tier | middleware in `app/main.py`, keyed off `Organization.plan_tier` |
| Clerk webhook sync (replacing lazy sync) | new `app/api/v1/webhooks_clerk.py` receiver |

</details>

<br/>

<details>
<summary><strong>More screenshots</strong></summary>

<br/>

<img src="docs/screenshot-forecast.png" alt="Crowd Forecast Studio — per-line heatmap and next network peak" width="100%" />

<br/><br/>

<img src="docs/screenshot-alerts.png" alt="Alerts & interventions — capacity breach predictions with recommended response" width="100%" />

</details>

<br/>

## Project structure

```
transit-crowding/
  frontend/                     # Flowcast — deployed dashboard (Vite, React + TS)
    index.html, styles.css, gradients.css
    src/
      App.tsx                   # React entry — portals into the legacy DOM
      main.tsx
      LiveMetrics.tsx           # small live-updating React components
      legacyInteractions.ts     # main interaction layer: map, planner, alerts, simulator
  backend/                      # TransitPulse — crowding model + multi-tenant API
    app/
      main.py                   # FastAPI app factory, router mounts, CORS
      config.py                 # pydantic-settings: DATABASE_URL, CLERK_*, CORS origins
      api/
        predict.py               # POST /predict — predict_best_effort(): trained model, heuristic fallback
        recommend.py             # GET /stations, POST /recommend-route
        v1/                      # orgs, members, api-keys, routes, trips, crowding
      ml/
        inference.py              # trained Random Forest — loading, nearest-neighbor lag lookups, predict_ridership()
        model.py                  # rule-based heuristic used by the separate /api/v1 crowding endpoint
        artifacts/                 # transit_crowding_model.joblib (pruned, 20 trees), feature_columns,
                                    # station_mapping, station_metadata.csv, model_metadata.json
      db/                        # declarative Base, SessionLocal, get_db
      models/                    # SQLAlchemy ORM — organizations, users,
                                  # memberships, api_keys, routes, stops,
                                  # trips, crowding_predictions
      schemas/                   # Pydantic request/response contracts
      auth/                      # Clerk JWT verification, API keys, RBAC
      data/
        synthetic_data.py         # org-parameterized synthetic GTFS generator (/api/v1 layer)
        flowcast_mta_data.csv     # real NYC MTA hourly ridership (128,803 rows) — trained-model lag features
      services/transit.py        # seeding + prediction refresh
      scripts/seed_dev_org.py    # local-only: bootstrap an org without Clerk
    alembic/                     # migrations
    requirements.txt             # production dependencies (incl. pandas/numpy/scikit-learn/joblib)
    requirements-dev.txt         # local-only extras (pgserver)
    .python-version              # pinned for Render's build image
    .env.example
  docs/
    screenshot-network.png
    screenshot-forecast.png
    screenshot-alerts.png
  README.md
```

<br/>

<div align="center">

**[Open the live demo →](https://flowcast-transit-ai.vercel.app)**

</div>
