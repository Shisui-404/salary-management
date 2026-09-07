# ADR-003: Static FX rate table, normalisation pushed into SQL

## Context
Compensation is stored per-employee in local currency, but every cross-country
comparison (dashboard totals, band-health, pay-equity, by-dimension) needs a
common `BASE_CURRENCY` (USD). At 10,000 employees, converting rows in Python
before aggregating would mean pulling the whole table into the application on
every analytics request — the scale requirement explicitly rules this out.

## Decision
`currency_rates(currency, rate_to_base, valid_from)` is a small, seeded,
static table — no live feed. `rate_to_base` means "how many `BASE_CURRENCY`
units one unit of `currency` is worth." Every query that needs a base-currency
amount joins against the *latest* rate per currency
(`repositories/currency_repo.latest_rates_subquery`) and computes
`amount_base = ROUND(amount_minor * rate_to_base)` **inside the SQL
statement**, so filtering, sorting and aggregating by base-currency salary
stay index/`ORDER BY`-driven, never a Python-side loop over fetched rows.
`services/fx.convert_minor_to_base` is the single pure function the SQL
expression mirrors, so both are unit-tested against the same formula.

## Consequences
- Analytics endpoints run one SQL statement each (or two, for the SQLite
  percentile fallback — see `analytics_repo.py`'s module docstring), not N.
- On SQLite, `rate_to_base` arithmetic inside a raw SQL expression is
  IEEE-754 double-backed (SQLite has no arbitrary-precision decimal type at
  the engine level) — an accepted, documented trade-off for *reporting*
  aggregates, which are not the money-of-record (that stays exact integer
  minor units — see ADR-001). On Postgres, `Numeric` arithmetic is exact.
- Salary bands are stored already in `BASE_CURRENCY` (see `seed/seed.py`),
  so band comparisons don't need a second FX join in the common case.

## Alternatives considered
- **Live FX feed**: adds a network dependency and non-deterministic tests
  for no gain in demonstrating the design; the conversion boundary
  (`fx.py` + the rate table) is isolated so swapping in a provider is a
  one-file change, noted as a "first thing to add" in requirements.md.
- **Convert and store every amount in `BASE_CURRENCY` redundantly**: would
  need re-writing on every rate change and loses the local-currency figure
  the HR manager actually wants to see (`CurrentSalary.amount`).
