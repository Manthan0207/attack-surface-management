# ASM Asset Discovery Service

SharkStriker backend take-home: **Attack Surface Management — Asset Discovery Service**.

A FastAPI microservice that manages domains, runs passive DNS discovery (A / AAAA / NS / MX) in the background, and exposes results through a JWT-secured, RBAC-aware API.

---

## Requirements

- Docker + Docker Compose
- (Optional for local tooling) Python 3.12+

---

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

On startup the API container:

1. Runs `alembic upgrade head`
2. Seeds a bootstrap admin if none exists (`ADMIN_*` env vars)
3. Starts discovery worker threads

### Default admin login

Values come from `.env` / Compose (see `.env.example`):

- Email: `admin@example.com`
- Password: `ChangeMeAdmin123!`

---

## Run tests

Tests use Postgres database `asm_test` (created automatically if missing) and mock DNS resolution.

With Compose already running (DB on `localhost:5432`):

```bash
# from the host (Python 3.12 + deps installed)
pip install -r requirements.txt
pytest
```

Or inside the API container (rebuild first if you changed test files — no source bind-mount):

```bash
docker compose up --build -d
docker compose exec -e TESTING=true -e DATABASE_URL=postgresql+psycopg://asm:asm@db:5432/asm_test api pytest
```

### CI (GitHub Actions)

On every push/PR to `main` (or `master`), `.github/workflows/test.yml` spins up Postgres 16, installs deps, and runs `pytest` with `TESTING=true` against `asm_test`.

---

## Architecture overview

```
Client
  │  JWT Bearer
  ▼
FastAPI (auth, domains, scans, assets, health)
  │
  ├─ PostgreSQL  (users, domains, scans, assets — source of truth)
  │
  └─ In-memory job queue ──► worker thread pool
                                │
                                └─ dnspython (A/AAAA/NS/MX) → persist assets
```

**Layers:** `api` → `services` → `repositories` / `workers` → SQLAlchemy models.

**Scan flow**

1. Domain create or `POST /domains/{id}/scan` inserts a `PENDING` scan and enqueues `scan_id`
2. A worker marks it `RUNNING`, resolves DNS, stores assets, then `COMPLETED` / `FAILED`
3. Domain status mirrors the active/latest scan outcome
4. Manual trigger uses `SELECT … FOR UPDATE` on the domain row and returns **409** if a scan is already `PENDING` or `RUNNING`

---

## Main API surface

| Method | Path | Access |
|---|---|---|
| POST | `/auth/login` | Public |
| POST | `/auth/register` | Admin |
| GET/POST | `/domains` | GET: all roles · POST: Admin/Analyst |
| GET/DELETE | `/domains/{id}` | GET: all · DELETE: Admin |
| POST | `/domains/{id}/scan` | Admin/Analyst → 202 |
| GET | `/domains/{id}/scans` | All roles |
| GET | `/assets` | All roles (`domain_id`, `type`, pagination) |
| GET | `/health` | Public |

---

## Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL (Compose overrides host to `db`) |
| `JWT_SECRET_KEY` | HMAC secret for access tokens |
| `JWT_ALGORITHM` | Default `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_FULL_NAME` | Bootstrap admin |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | List pagination |
| `DNS_TIMEOUT_SECONDS` | Per-lookup DNS timeout |
| `DISCOVERY_WORKER_THREADS` | Background worker count |
| `TESTING` | Set `true` in pytest to skip workers |
| `DEBUG` | FastAPI debug flag |

See `.env.example` for a full template.

---

## Design decisions & trade-offs

1. **In-memory queue + thread pool** — Simple baseline that keeps blocking `dnspython` off the asyncio event loop. Scan/asset state lives in Postgres; the queue is rebuilt from `PENDING` / interrupted `RUNNING` rows on startup. Swap-ready for Redis/Celery later.
2. **Admin seed from env** — Idempotent startup seed avoids putting secrets in Alembic data migrations.
3. **Scan concurrency** — API serializes manual triggers with `FOR UPDATE` and treats `PENDING` as in-flight so parallel `POST /scan` cannot both return 202. Worker side claim locking was deferred.
4. **One scan resolves all four record types** — A single job queries A, AAAA, NS, and MX and stores every answer as its own asset row.

---
