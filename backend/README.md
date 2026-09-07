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

## Performance (measured, 10,000 employees / ~19.8k salary records, SQLite)

Measured three times, because the first two readings each pointed at the
wrong thing. Numbers are three warm runs against the seeded 10,000-employee
dataset.

End-to-end HTTP latency, three warm runs each, 10,000 employees / 19,794
salary records:

| Endpoint | On `/mnt/c` (NTFS via WSL) | Native FS, before query fix | Native FS, after |
|---|---|---|---|
| `GET /employees?limit=25` (default sort) | ~500ms | ~42–88ms | **~17–19ms** |
| `GET /employees` filtered | ~410ms | ~21–28ms | **~13ms** |
| `GET /employees/{id}` | ~16ms | ~5–13ms | **~8ms** |
| `GET /analytics/summary` | ~450ms | ~68–100ms | ~68–100ms |
| `GET /analytics/distribution` | ~450ms | ~67–90ms | ~67–90ms |
| `GET /analytics/by-dimension` | ~2,980ms | ~77–90ms | ~77–90ms |
| `GET /analytics/pay-equity` | ~440ms | ~55–78ms | ~55–78ms |
| `GET /analytics/band-health` | ~415ms | ~53–64ms | ~53–64ms |
| Seed 10,000 employees | — | — | **~2.1s** |

Endpoints measured only after the fix: `GET /employees?sort=-salary` ~47ms,
`GET /employees?offset=9000` ~26ms, `GET /employees?search=an` ~34ms.

At the query level, measured in-process so the numbers isolate the SQL rather
than HTTP and serialisation:

| Query | Before | After |
|---|---|---|
| Page of 25, default sort | ~30ms | **~9.6ms** |
| Its `total` count | ~26ms | **~0.4ms** |
| Page of 25, `sort=-salary` | ~28ms | ~40ms |

Two separate things were wrong, and it took two rounds of measurement to
separate them.

**The filesystem.** The checkout lives on a Windows drive mounted into WSL.
SQLite issues many small reads and that mount makes each one expensive: a bare
`SELECT COUNT(*)` costs 23ms there against 0.4ms on ext4, and an indexed join
scan 80ms against 2.4ms. That is a ~30x tax before any application code runs,
and it accounted for most of the first column.

**The query shape.** Having found the filesystem effect, the first write-up
concluded the queries themselves were fine. A later review showed that was
only half right. `EXPLAIN QUERY PLAN` on the list query ends in
`USE TEMP B-TREE FOR ORDER BY` *after* every join — SQLite built all 10,000
joined rows (including two materialised FX-rate subqueries), sorted them, then
discarded all but 25. The count query paid that same cost to produce a number
that needed no joins at all.

The fix, in `repositories/employee_repo.py`:
- `count_matching` counts over `employees` alone unless a filter actually
  depends on compensation data (only `band_position` and the salary-range
  filters do). 26ms → 0.4ms.
- `get_page_rows` selects the page of **ids** first, from `employees` alone,
  then applies the wide join to just those 25 rows — O(page size) instead of
  O(all employees) per page load.
- Sorting by `salary` or `compa_ratio`, or filtering by band, genuinely needs
  the join to decide *which* rows belong on the page, so those keep the single
  joined query. Splitting them in two was measured and was slower, because it
  pays the join cost twice.
- Every sort now carries `Employee.id` as a final tie-break, so employees with
  equal sort keys have a total order and OFFSET paging cannot repeat or skip a
  row.

**One deliberate regression.** The tie-break costs about 12ms on the
compensation sorts (28ms → 40ms) and ~1.6ms on the default sort, because it
adds a second term to the ORDER BY. It is kept: unstable pagination silently
shows one employee twice and hides another, which is a much worse failure in a
salary tool than 12ms on a non-default sort. The cost is stated here rather
than left for someone to rediscover.

Inlining the FX rates as a `CASE` expression instead of two subquery joins was
measured too (13.6ms → 11.2ms on the salary sort) and rejected: the remaining
cost is the unavoidable scan-and-sort, so it was not worth the churn.

The honest summary is that the first conclusion — "it's the mount, the query
is fine" — was a plausible story that was only half true, and it took someone
re-measuring the query shape in isolation to find the other half.

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
