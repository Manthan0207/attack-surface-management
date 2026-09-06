# ASM Asset Discovery Service

SharkStriker backend take-home: **Attack Surface Management — Asset Discovery Service**.

A FastAPI microservice that manages domains, runs passive DNS discovery (A / AAAA / NS / MX) in the background, and exposes results through a JWT-secured, RBAC-aware API.

---

## Requirements

- Docker + Docker Compose

---

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Starts **Postgres**, **Redis**, **API**, and a **Celery worker**.

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

On startup the API container:

1. Runs `alembic upgrade head`
2. Seeds a bootstrap admin if none exists (`ADMIN_*` env vars)
3. Re-queues any interrupted `PENDING` / `RUNNING` scans into Celery

### Default admin login

Values come from `.env` / Compose (see `.env.example`):

- Email: `admin@example.com`
- Password: `ChangeMeAdmin123!`

---

## Run tests

Tests use Postgres database `asm_test` (created automatically if missing) and mock DNS resolution. Discovery runs **inline** (Celery is not required for pytest).

Run tests **inside the API container** :

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
  └─ Redis (Celery broker) ──► Celery worker process
                                  │
                                  └─ dnspython (A/AAAA/NS/MX) → persist assets
```

**Layers:** `api` → `services` → `repositories` / `workers` → SQLAlchemy models.

**Scan flow**

1. Domain create or `POST /domains/{id}/scan` inserts a `PENDING` scan and enqueues `scan_id` via Celery
2. Worker marks it `RUNNING`, resolves DNS, stores assets, then `COMPLETED` / `FAILED`
3. Transient DNS errors are retried by Celery (`SCAN_MAX_RETRIES`)
4. Domain status mirrors the active/latest scan outcome
5. Manual trigger uses `SELECT … FOR UPDATE` on the domain row and returns **409** if a scan is already `PENDING` or `RUNNING`

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
| `CELERY_BROKER_URL` | Redis broker for Celery |
| `CELERY_RESULT_BACKEND` | Redis result backend |
| `SCAN_MAX_RETRIES` | Celery retries for transient DNS failures |
| `SCAN_RETRY_BACKOFF_SECONDS` | Delay between retries |
| `JWT_SECRET_KEY` | HMAC secret for access tokens |
| `JWT_ALGORITHM` | Default `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_FULL_NAME` | Bootstrap admin |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | List pagination |
| `DNS_TIMEOUT_SECONDS` | Per-lookup DNS timeout |
| `TESTING` | Set `true` in pytest to skip Celery recovery |
| `LOGIN_RATE_LIMIT` | Max `POST /auth/login` attempts per IP per window |
| `LOGIN_RATE_WINDOW_SECONDS` | Sliding window for login rate limit |
| `DEBUG` | FastAPI debug flag |

See `.env.example` for a full template.

---

## Design decisions & trade-offs

1. **Celery + Redis** — Discovery runs in a separate worker process so blocking DNS stays off the API event loop. Scan/asset state stays in Postgres; Redis only brokers job IDs. Interrupted scans are re-queued from DB on API startup.
2. **Admin seed from env** — Idempotent startup seed avoids putting secrets in Alembic data migrations.
3. **Scan concurrency** — API serializes manual triggers with `FOR UPDATE` and treats `PENDING` as in-flight so parallel `POST /scan` cannot both return 202.
4. **One scan resolves all four record types** — A single job queries A, AAAA, NS, and MX and stores every answer as its own asset row.
5. **Login rate limit** — In-memory per-IP budget on `POST /auth/login` (429 when exceeded). Process-local; Redis later for multi-instance API.
6. **DNS retries** — Celery retries timeouts / DNS errors up to `SCAN_MAX_RETRIES`, then marks the scan `FAILED`.

---

## Future improvements

- **Revoke Celery jobs on domain delete** — Today delete cascades scans/assets in Postgres; a leftover Redis message is a no-op when the worker finds the scan gone. Next step: store `celery_task_id` on the scan and `revoke` active tasks on delete (with the existing “scan not found” guard as backup).
- **RabbitMQ as Celery broker** — Redis was chosen for simple Compose setup. RabbitMQ is a stronger fit at higher volume: durable queues, routing, dead-letter exchanges, and clearer delivery semantics. Postgres would remain the source of truth for scan/asset state.
- **Shared login rate limit** — Move the in-memory limiter to Redis so it works across multiple API replicas.
- **Stronger scan claiming** — DB-level claim / partial unique index so only one worker can mark a scan `RUNNING` under concurrency.
  
---
