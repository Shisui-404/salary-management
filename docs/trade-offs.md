# Trade-offs and performance notes

Every entry here is a decision that could reasonably have gone the other way.

## Product trade-offs

**Analytics over breadth of CRUD.** The brief asks for software to manage salaries *and* answer
questions about how the org pays people. Spreadsheets already do the first part adequately, so
the effort went into the second: pay equity, band health, distribution and per-dimension
breakdowns. The cost is that some administrative features an HR product would eventually need
(bulk edit, saved views, org-chart navigation) are absent.

**No authentication.** The single largest deliberate omission. One known persona, no
multi-tenancy, and auth is a solved problem that would have consumed budget without
demonstrating anything about compensation-domain judgement. It is the first thing to add before
any real deployment — the API is entirely unprotected as it stands, which is fine for an
assessment and unacceptable in production.

**Pay equity computed within role and level, not org-wide.** An org-wide gender pay gap mostly
measures *role mix* rather than pay decisions, and quoting it as a pay-fairness figure would be
misleading. The API returns both: an overall headline figure and per-(role, level) groups where
comparison is meaningful. Groups with fewer than five people on either side are suppressed and
counted, not silently dropped — a 100% "gap" derived from two people is worse than no number.

**Salary means annual gross base only.** No bonus, equity or benefits. Adding components would
multiply the data model; base salary is the dimension an HR manager compares on first, and the
schema leaves room to add a component table later.

## Technical trade-offs

**Integer minor units instead of `Decimal` columns or floats.** Floats are disqualified outright
for money. `Numeric` columns would also work, but integers are exact in every dialect, compare
and sum trivially in SQL, and force the rounding decision to a single explicit boundary. Cost:
every read and write crosses a conversion layer, which is why `services/money.py` exists and is
the most heavily unit-tested module in the codebase.

**Effective-dated salary records instead of a `salary` column.** A column would have been far
less code. It also makes "what did we pay her in March 2024?" unanswerable and destroys the
audit trail on every raise — and history is exactly what an HR manager needs during a review
cycle. Cost: "current salary" is a join rather than a column, mitigated by a partial index on
`(employee_id) WHERE effective_to IS NULL`, and the close-and-insert must be transactional.

**No migrations tool.** `create_all` plus a seed script. Alembic is the right answer for a system
with real data to preserve, but this project has a single schema generation and a reproducible
seed, so a migrations directory would be ceremony rather than safety. This is the decision most
likely to be wrong in a real deployment, and it is recorded as such in ADR-004.

**SQLite by default, Postgres-compatible.** SQLite keeps setup to zero commands and tests fast.
The one real consequence is percentiles: Postgres has `percentile_cont`, SQLite does not, so
there is an explicit Python fallback that fetches only the single ordered salary column. Both
paths are tested against the same expected values.

**Static FX rates in a dated table.** A live rate feed would add a network dependency, a failure
mode and non-deterministic tests, for no gain in demonstrating design. Conversion is isolated
behind `services/fx.py`, so swapping in a provider is a one-file change.

**CSV import never changes salary on an existing employee.** Import creates salary only for new
employees; updates touch non-salary attributes only. Letting a spreadsheet silently overwrite
compensation would defeat the append-only history that is the point of the salary model. Raises
go through `POST /employees/{id}/salary`, which records reason and effective date.

## Performance at 10,000 employees

Measured against the seeded dataset (10,000 employees, 19,794 salary records), three runs each.

| Endpoint | On `/mnt/c` (NTFS via WSL) | On a native Linux filesystem |
|---|---|---|
| `GET /employees?limit=25` | ~500ms | **~42–88ms** |
| `GET /employees` filtered + sorted | ~410ms | **~21–28ms** |
| `GET /employees/{id}` | ~16ms | **~5–13ms** |
| `GET /analytics/summary` | ~450ms | **~68–100ms** |
| `GET /analytics/distribution` | ~450ms | **~67–90ms** |
| `GET /analytics/by-dimension` | ~2,980ms | **~77–90ms** |
| `GET /analytics/pay-equity` | ~440ms | **~55–78ms** |
| `GET /analytics/band-health` | ~415ms | **~53–64ms** |
| Seed 10,000 employees | — | **~2.1s** |

The first column was measured first, and it prompted a wrong conclusion: that the cost was the
inherent width of the join on SQLite. It was not. The checkout lives on a Windows drive mounted
into WSL, and SQLite issues many small reads that the mount makes expensive — a bare
`SELECT COUNT(*)` costs 23ms there against 0.4ms on ext4, and an indexed join scan 80ms against
2.4ms. Copying the same database file to a native filesystem and running the same binary
produced the second column: `by-dimension` improved 35x with no code change.

The design points that make the second column possible:
- Pagination, filtering and sorting are pushed into SQL; no endpoint materialises the table.
- Current salary resolves through a partial index rather than a per-row subquery, so the list
  endpoint has no N+1.
- Analytics aggregate in SQL with the FX rate joined inline.
- `analytics_repo.get_summary` computes headcount, active headcount, sum, min, max and distinct
  counts in one query rather than three.

Deliberately not pursued, because the numbers do not justify them at this scale: a denormalised
read model for the directory, response caching for analytics, and moving to Postgres.

## What I would do next, in order

1. Authentication and role-based access — the app is currently open.
2. Alembic migrations, before any data exists that matters.
3. Postgres in production, which also removes the percentile fallback.
4. An `audit_log` table covering non-salary edits (salary is already append-only).
5. Salary components (bonus, equity) as a related table rather than more columns.
