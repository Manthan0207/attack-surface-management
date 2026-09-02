# ASM asset discovery service

## Run with Docker

1. Copy env template: `cp .env.example .env` (Windows: `copy .env.example .env`)
2. Start stack: `docker compose up --build`
3. Open API docs: http://localhost:8000/docs

Services:
- `api` — FastAPI on port `8000`
- `db` — PostgreSQL 16 on port `5432` (healthy before API starts)

Database URL inside Compose uses host `db`. Local non-Docker runs can keep `localhost` from `.env`.
