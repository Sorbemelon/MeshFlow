# MeshFlow v2 Backend

Phase 1 backend skeleton for the warehouse-first MeshFlow v2 rebuild.

This backend is intentionally small. It provides only the application foundation:

- FastAPI app factory and API router
- settings management
- structured error response model
- SQLAlchemy metadata database connection
- Alembic migration structure
- health endpoints
- basic tests

It does **not** implement dataset upload, Snowflake loading, dbt transformations, AI providers, analysis runs, or dashboard logic yet.

## Non-negotiable rules

- No DuckDB.
- No local analytics execution.
- No mock success path.
- No deterministic fake analysis fallback.
- Warehouse-dependent workflows must fail honestly when S3, Snowflake, dbt, or AI providers are not configured.

The local SQLite default is for metadata-development convenience only. It is not an analytical execution engine and must not be used to produce analysis results.

## Setup

From the `backend/` folder:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest
```

Run Alembic after the first migration exists:

```bash
alembic upgrade head
```

Create a migration later:

```bash
alembic revision --autogenerate -m "add initial metadata tables"
```

## Health endpoints

```text
GET /health
GET /api/v1/health
GET /api/v1/health/db
```

## Expected Phase 1 behavior

`/health` and `/api/v1/health` should return `ok` when the backend app is reachable.

`/api/v1/health/db` should return `ok` when the metadata database connection can execute a simple `SELECT 1`.

Warehouse/S3/dbt/AI readiness endpoints are intentionally not implemented until later phases.
