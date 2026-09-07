# Plan — ACME Salary Management (Incubyte Assessment)

## Context

The assignment (`Salary Management Assessment.pdf`) asks for end-to-end salary management
software for an org of 10,000 employees, persona **HR Manager of ACME**. Today they manage
salary data for 10k employees across multiple countries in Excel; they want web software to
manage that data **and to answer questions about how the org pays people**.

The PDF grades on: clarity of thinking, product thinking, architecture/design decisions,
production-quality code and tests, incremental commits, committed artifacts (requirements doc,
design notes, AI prompts, trade-offs), a seed script with 10k employees, and a deployed build +
demo video. Explicitly: *"We are not looking for the most complex system, but for good
engineering judgment."*

The working directory is currently **empty and not a git repo** — this is a greenfield build.

Decisions confirmed with the user:
- Backend: **Python + FastAPI** (SQLAlchemy, pytest)
- Frontend: **Next.js + TailwindCSS + shadcn/ui**
- Scope: **Core CRUD + salary history + multi-currency + compensation analytics**
- Deployment: **Docker Compose + written deploy notes** (user runs the actual cloud deploy)

## Product framing (drives every technical choice)

The differentiator is not CRUD — it is the *analytics* half: an HR manager must be able to ask
"how do we pay people?" and get a defensible answer. Concretely the app answers:
band/percentile position of any employee, spread and outliers per role+level+country,
gender/geo pay gaps, compa-ratio vs. band midpoint, and payroll cost roll-ups — all
currency-normalised so cross-country comparison is meaningful.

Deliberately **out of scope** (stated with reasons in the requirements doc): authn/authz &
RBAC, approval workflows, payroll execution/payslips, taxes & statutory deductions, equity/
bonus modelling, live FX rate feeds, i18n, and audit trails beyond salary history.

## Architecture

```
salary-management/
├── docs/                      # graded artifacts
│   ├── requirements.md        # the one-page requirements doc (write FIRST, commit FIRST)
│   ├── architecture.md        # C4-ish context + component diagram (mermaid), data model
│   ├── decisions/ADR-00x.md   # short ADRs: money type, effective-dated salary, FX, pagination
│   ├── trade-offs.md          # what we chose not to do and why; performance notes
│   └── ai-usage.md            # prompts/instructions used, what AI got wrong, how it was verified
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app factory, CORS, exception handlers
│   │   ├── core/config.py     # pydantic-settings (DATABASE_URL, BASE_CURRENCY, CORS)
│   │   ├── db/session.py      # engine + session dependency
│   │   ├── models/            # SQLAlchemy 2.0 ORM: Employee, Department, JobRole/Level,
│   │   │                      #   Country, SalaryRecord, CurrencyRate, SalaryBand
│   │   ├── schemas/           # Pydantic v2 request/response DTOs
│   │   ├── repositories/      # query layer (keeps SQL out of routers/services)
│   │   ├── services/          # domain logic: salary_service, analytics_service, money, fx
│   │   ├── api/v1/routers/    # employees, salaries, analytics, reference, imports
│   │   └── seed/seed.py       # deterministic 10k-employee generator
│   └── tests/                 # pytest: unit (pure domain) + api (TestClient, SQLite)
├── frontend/                  # Next.js App Router + Tailwind + shadcn/ui + TanStack Query/Table
├── docker-compose.yml         # postgres + backend + frontend
└── README.md                  # run, test, seed, deploy, demo-video link
```

### Domain model (key decisions)

- **Money is never a float.** Store `amount_minor` as `BigInteger` (minor units) + ISO-4217
  `currency` code; convert at the edge with `Decimal`. ADR-001.
- **Salary is effective-dated, never overwritten.** `SalaryRecord(employee_id, amount_minor,
  currency, effective_from, effective_to NULL, change_reason, created_at)`. A raise closes the
  open row and inserts a new one in one transaction. Current salary = row where
  `effective_to IS NULL`. This makes history, "as-of" queries, and audit fall out for free.
  ADR-002.
- **FX**: a `currency_rates` table of rates to a base currency (`BASE_CURRENCY=USD`), seeded
  with static rates and a `valid_from` date. No live feed (documented trade-off); normalised
  amounts are computed in SQL for aggregation, so analytics stays a single query. ADR-003.
- **Salary bands**: `(job_role, level, country) → min/mid/max` in base currency, enabling
  compa-ratio and "outside band" flags — the core product-thinking hook.
- **Reference data** (department, role, level, country) as small tables + FKs so filters and
  group-bys are index-backed rather than string matching.

### API surface (`/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/employees` | server-side pagination, search (name/email/code), filters (dept, country, role, level, status, salary range), sort; returns current salary + compa-ratio |
| GET | `/employees/{id}` | detail + full salary history |
| POST/PATCH | `/employees`, `/employees/{id}` | create / update non-salary attributes |
| POST | `/employees/{id}/salary` | raise/adjustment: closes current record, opens new one |
| GET | `/employees/{id}/salary-history` | effective-dated timeline |
| GET | `/analytics/summary` | headcount, total annual payroll, median/mean, YoY change |
| GET | `/analytics/distribution` | histogram + p10/p25/p50/p75/p90 by dimension |
| GET | `/analytics/by-dimension` | group by department / country / role / level: count, median, spread |
| GET | `/analytics/pay-equity` | median gap % by gender within role+level (with sample-size guard) |
| GET | `/analytics/band-health` | % below / within / above band, outlier list |
| GET | `/employees/export` | CSV export of the current filter |
| POST | `/employees/import` | CSV bulk upsert with per-row validation report |

Errors: RFC-7807-ish JSON problem responses via a single exception handler; domain errors
(`SalaryEffectiveDateOverlap`, `EmployeeNotFound`, …) raised from services, mapped in one place.

### Scale (10k employees) — deliberate, documented choices

- Never load all rows: every list endpoint is keyset-friendly, `limit`-capped, with a `total`
  from a separate count query.
- Indexes on `salary_records(employee_id, effective_to)` (partial `WHERE effective_to IS NULL`
  on Postgres), and on employee filter columns.
- Analytics aggregates run **in SQL**, not Python — percentiles via `percentile_cont` on
  Postgres with a portable Python fallback for SQLite (documented in `trade-offs.md`).
- Seed uses a fixed RNG seed + bulk inserts in batches (~2k) so 10k employees + ~25k salary
  records load in seconds and are byte-identical run-to-run (makes tests and screenshots stable).

### Frontend

- `/` Dashboard: KPI tiles (headcount, annual payroll, median, band coverage), salary
  distribution histogram, median-by-department bar, pay-gap panel, band-health panel.
- `/employees` Directory: server-side paginated TanStack Table, debounced search, faceted
  filters, sort, CSV export, "Add employee".
- `/employees/[id]` Profile: details, current comp with compa-ratio + band position gauge,
  salary history timeline, "Record a raise" dialog with optimistic invalidation.
- Recharts for charts; loading skeletons, empty states, error boundaries, toasts.
- Typed API client generated from the OpenAPI schema (or a thin hand-written typed fetch layer
  if generation adds friction).

## Testing strategy

Fast and deterministic, no network, no sleeps:
- **Unit (pure functions, no DB)**: money arithmetic and rounding, FX normalisation,
  percentile/median maths, compa-ratio & band classification, pay-gap calculation incl. the
  small-sample guard, CSV row validation. These are the tests that show engineering
  fundamentals — table-driven with `pytest.mark.parametrize`, covering edge cases (empty set,
  single employee, ties, zero/negative amounts, unknown currency).
- **Service tests**: salary revision closes the prior record, rejects overlapping/back-dated
  effective dates, history ordering, as-of lookup.
- **API tests**: FastAPI `TestClient` over an in-memory/temp SQLite created per test via
  fixtures; pagination/filter/sort contract, validation 422s, error shape, import report.
- **Frontend**: Vitest + Testing Library on the pure formatting/derivation helpers and a couple
  of key components (filter state → query params; table rendering) — kept small on purpose.
- CI: a GitHub Actions workflow running ruff + pytest (+ frontend lint/test).

## Delivery order (each step = one commit; history is graded)

1. `docs/requirements.md` (one-pager: goal, scope, out-of-scope + reasons) — **before code**.
2. Repo scaffold: git init, backend/frontend skeletons, tooling (ruff, pytest, .env.example), README.
3. Domain models + migrations/`create_all` + reference data.
4. Money/FX + band/compa-ratio domain services **with their unit tests** (test-first here).
5. Employee CRUD + list endpoint (pagination/filter/sort) + API tests.
6. Effective-dated salary revision + history endpoints + tests.
7. Seed script for 10,000 employees; verify list p95 latency and record it in `trade-offs.md`.
8. Analytics endpoints + tests (summary, distribution, by-dimension, pay-equity, band-health).
9. CSV import/export + validation tests.
10. Frontend: shell/layout → employee directory → employee profile + raise flow → dashboard.
11. Docker Compose, deploy notes, CI workflow.
12. Artifacts: `architecture.md` + mermaid diagrams, ADRs, `trade-offs.md`, `ai-usage.md`,
    README polish, demo-video placeholder + script.

A copy of this plan is committed to the repo as `Plan.md` in step 1 (the user asked for it by
name), with `docs/` holding the deeper artifacts.

## Verification

- `cd backend && pytest -q` — all green, runs in a few seconds, no network.
- `python -m app.seed.seed --count 10000` then `GET /api/v1/employees?limit=50` returns in
  well under ~300 ms; `/analytics/summary` likewise. Numbers recorded in `trade-offs.md`.
- `uvicorn app.main:app --reload` + `/docs` — exercise every endpoint from Swagger.
- `npm run dev` in `frontend/` against the local API; walk the three screens, record a raise and
  confirm the history + dashboard update.
- `docker compose up --build` from a clean checkout brings up Postgres + API + UI and auto-seeds.
- `ruff check` / `npm run lint` clean.

## Environment notes / risks

- `node` is **not** on the WSL PATH; only the Windows install at
  `/mnt/c/Program Files/nodejs/node.exe` (v24.13.1, npm 11.8) is reachable. The project lives on
  the C: drive, so frontend commands will be run through the Windows binaries. If that proves
  flaky, the fallback is to install Node inside WSL — will confirm with the user before doing so.
- `pip` is missing from the WSL Python 3.14; backend deps go in a venv
  (`python3 -m venv .venv` ships `ensurepip`). Python 3.14 is very new — if any dependency lacks
  wheels, I'll pin to a 3.12 venv and say so.
- Docker is not installed in this environment, so `docker compose up` is written and reviewed but
  cannot be executed here; everything else is verified locally.
