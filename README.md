# ACME Salary Management

Salary management for a 10,000-employee, multi-country organisation — built for the Incubyte
assessment. Backend: **FastAPI + SQLAlchemy**. Frontend: **Next.js + shadcn/ui**.

The product is built around the second half of the brief: not just storing salaries, but
answering *how does this organisation pay people?* — pay equity, band health, distribution and
cross-currency comparison.

## Quick start

### Option A — Docker (one command)

```bash
docker compose up --build
```
UI on http://localhost:3000, API on http://localhost:8000 (docs at `/docs`). The backend seeds
10,000 employees on first start, and the UI waits for the API's health check before booting.

### Option B — Local

```bash
# Backend  (http://localhost:8000)
cd backend
python -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m app.seed.seed --count 10000 --reset
.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# Frontend (http://localhost:3000)
cd frontend
npm install
npm run dev
```

> **Note for WSL users:** keep the SQLite database on a native Linux filesystem, not under
> `/mnt/c`. The mount adds ~30x latency to SQLite's small reads — see
> [`docs/trade-offs.md`](docs/trade-offs.md) for the measurements. Set
> `DATABASE_URL=sqlite:////home/you/salary.db`.

## Tests

```bash
cd backend  && .venv/bin/python -m pytest -q     # 243 tests, ~17s
cd backend  && .venv/bin/python -m ruff check .
cd frontend && npm test                          # 44 tests
cd frontend && npm run lint && npm run build
```

## What it does

| Area | Capability |
|---|---|
| Directory | 10,000 employees with server-side pagination, search, faceted filters and sort; state kept in the URL so views are shareable |
| Employee profile | Full attributes, current compensation, band-position gauge, compa-ratio |
| Salary history | Effective-dated, append-only timeline with change reason and % change |
| Raises | Recording a raise closes the current record and opens a new one in one transaction — nothing is ever overwritten |
| Multi-currency | Salaries stored in local currency, normalised to a base currency for every comparison |
| Analytics | Payroll summary, distribution with percentiles, per-dimension breakdown, pay equity, band health with an outlier list |
| Data movement | CSV export of any filtered view; CSV import with per-row validation reporting |

## Documentation

| Document | What's in it |
|---|---|
| [`docs/requirements.md`](docs/requirements.md) | The one-page requirements doc: goal, persona, scope, and **what is deliberately left out and why** |
| [`docs/api-contract.md`](docs/api-contract.md) | The API spec, written before the code and used as the contract between backend and frontend |
| [`docs/architecture.md`](docs/architecture.md) | Context, component and ER diagrams; the three decisions that shape the system; scale approach |
| [`docs/trade-offs.md`](docs/trade-offs.md) | Decisions that could have gone the other way, with measured performance numbers |
| [`docs/decisions/`](docs/decisions/) | ADRs: money representation, effective-dated salary, FX normalisation, no migrations tool |
| [`docs/ai-usage.md`](docs/ai-usage.md) | How AI tools were used, and what they got wrong |
| [`docs/demo-script.md`](docs/demo-script.md) | Script for the demo video |
| [`Plan.md`](Plan.md) | The implementation plan written before building |

## Design decisions worth knowing up front

**Money never touches a float.** Amounts are stored as integer minor units with an ISO-4217
code and cross the API as decimal strings, so neither Python nor JavaScript can round them
wrong. → [ADR-001](docs/decisions/ADR-001-money-representation.md)

**Salary is an append-only timeline, not a column.** `effective_to IS NULL` marks the current
record. A raise closes the open row and inserts a new one atomically, which is what makes
history, audit and as-of queries possible. → [ADR-002](docs/decisions/ADR-002-effective-dated-salary.md)

**Currency normalisation happens in SQL.** Aggregates join a dated rate table rather than
converting in Python, so cross-country analytics stays a single query at any scale.
→ [ADR-003](docs/decisions/ADR-003-fx-normalisation.md)

**Pay gaps are computed within comparable role and level**, with small groups suppressed and
counted. An org-wide gender gap mostly measures role mix, and reporting it as a fairness
number would be misleading.

## Repository layout

```
backend/    FastAPI service — api/ → services/ → repositories/ → models/
frontend/   Next.js App Router UI
docs/       Requirements, contract, architecture, ADRs, trade-offs
```

## Deployment

`docker-compose.yml` runs Postgres, the API and the UI with health-gated startup ordering. The
backend is dialect-agnostic: SQLite locally, Postgres in the composed stack. CI
(`.github/workflows/ci.yml`) runs ruff + pytest and the frontend's lint, tests and build on
every push.
