# ASM Asset Discovery Service

SharkStriker backend take-home: Attack Surface Management — Asset Discovery Service.

## Run with Docker

1. Copy env template: `cp .env.example .env` (Windows: `copy .env.example .env`)
2. Start stack: `docker compose up --build`
3. Open API docs: http://localhost:8000/docs
4. Health check: http://localhost:8000/health

On startup the API container:
- runs `alembic upgrade head`
- seeds a bootstrap admin if none exists (from `ADMIN_*` env vars)

Services:
- `api` — FastAPI on port `8000`
- `db` — PostgreSQL 16 on port `5432`
