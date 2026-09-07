# ACME Salary Management — Backend

FastAPI backend for the ACME salary-management app: an employee directory
with effective-dated, multi-currency salary history, and the compensation
analytics (bands, pay-equity, distribution) described in
`../docs/requirements.md`. Implements `../docs/api-contract.md` exactly.

## Stack

Python 3.12+, FastAPI, SQLAlchemy 2.0 (`Mapped`/`mapped_column`, `select()`),
Pydantic v2, SQLite by default / Postgres-ready, pytest, ruff.

## Setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # defaults already work; edit if you want Postgres
```

## Run

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Interactive API docs: `http://localhost:8000/docs`. Every endpoint lives
under `/api/v1` (see `../docs/api-contract.md`); `GET /health` is available
both at `/api/v1/health` (the contract path) and unversioned at `/health`
(for container/orchestrator health checks).

## Seed data

```bash
.venv/bin/python -m app.seed.seed --count 10000 --reset
```

Generates 8 countries, 9 departments, 23 job roles, 6 levels, and 10,000
employees with 1–4 salary records each — fully deterministic (fixed RNG
seed, dates anchored to a fixed reference date, never `date.today()`), so
re-running with the same `--count` produces byte-identical data. Completes
in well under a second on SQLite. See the module docstring in
`app/seed/seed.py` for the two deliberately injected signals (a small
gender pay gap, a handful of out-of-band outliers) that make the analytics
screens show something real.

Drop `--reset` to seed only if the database is currently empty (a no-op,
printing a message, if it already has employees).

## Test

```bash
.venv/bin/python -m pytest -q          # ~240 tests, a few seconds
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
```

- `tests/unit/` — pure functions, no database: money rounding, FX
  conversion, percentile/median math, compa-ratio and band classification,
  CSV row validation. Table-driven (`pytest.mark.parametrize`).
- `tests/api/` — FastAPI `TestClient` against a fresh temp-file SQLite
  database per test, with a hand-built ~12-employee fixture org whose
  expected numbers (sums, medians, percentiles, pay-equity gaps) are worked
  out by hand and asserted exactly.

## Lint

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

## Environment variables

See `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./salary.db` | SQLAlchemy URL. Postgres: `postgresql+psycopg://user:pass@host:5432/db` |
| `BASE_CURRENCY` | `USD` | Currency all normalised/comparison figures are reported in |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

## Docker

```bash
docker build -t acme-salary-backend .
docker run -p 8000:8000 -e DATABASE_URL=sqlite:////data/salary.db acme-salary-backend
```

Base image is `python:3.12-slim`. Setting `SEED_ON_START=true` (with an
optional `SEED_COUNT`, default 10000) runs the seed script before `uvicorn`
starts — see `../docker-compose.yml` for the full stack (Postgres + backend
+ frontend), which sets exactly that.

## Architecture

```
app/
  main.py               # app factory, CORS, routers, exception handlers
  core/                  # settings, error types + handlers, utc time helper
  db/session.py          # engine, SessionLocal, get_db dependency, Base
  models/                # SQLAlchemy 2.0 ORM
  schemas/                # Pydantic v2 request/response DTOs (matches the contract)
  repositories/           # all SQL/query construction
  services/               # domain logic: money, fx, bands, stats, salary/employee/analytics
                           # services, csv_io
  api/v1/routers/         # employees, salaries (part of employees.py), analytics, reference, health
  seed/                   # deterministic seed generator + its static reference data
tests/
  unit/                   # pure, no DB
  api/                    # FastAPI TestClient + temp SQLite + fixture org
```

Layering: routers depend on services, services depend on repositories,
repositories are the only place SQL/`select()` statements live. Domain rules
(money, FX, band classification, percentiles) are pure functions in
`services/`, unit-testable with no database.

## Design decisions

See `../docs/decisions/ADR-001..004` for money representation,
effective-dated salary, FX normalisation, and why there's no migrations
tool. `../docs/requirements.md` covers product scope and what's
deliberately out of scope (and why).
