# ADR-001: Money as integer minor units, never a float

## Context
The system stores and compares salaries across currencies and computes aggregates
(sums, means, percentiles) over thousands of them. Floating-point binary
representation cannot represent most decimal fractions exactly (`0.1 + 0.2 !=
0.3`), so any float-based arithmetic on money accumulates silent rounding error —
unacceptable for a system whose entire value proposition is "trust the numbers."

## Decision
Every monetary column (`SalaryRecord.amount_minor`, `SalaryBand.*_minor`) is a
`BigInteger` storing the amount in minor units (cents/paise/...), paired with a
3-letter ISO-4217 `currency` column. All parsing/formatting/rounding funnels
through `services/money.py`, which uses `decimal.Decimal` with explicit
`ROUND_HALF_UP` quantisation to 2 decimal places. The API never emits a JSON
number for money — always a decimal string (`"2400000.00"`).
Every currency is treated as having 2 minor-unit decimal places uniformly
(real ISO-4217 has 0 for JPY, 3 for BHD, etc.) — a deliberate simplification
appropriate for a compensation system, not a payment processor.

## Consequences
- No money value can silently drift; every conversion is a pure, unit-tested function.
- SQL aggregates run on integers/exact `Numeric`, not floats, wherever the
  dialect supports it (Postgres `Numeric`; SQLite's dynamic typing means FX
  join arithmetic is float-backed there — documented in ADR-003).
- Slightly more verbose than `float`/`Decimal` columns directly, but the
  boundary (`money.py`) is small, isolated and heavily tested.

## Alternatives considered
- **`Decimal`/`Numeric` column directly**: still float-backed on SQLite at
  the byte level; minor units keep every DB in this system doing exact
  integer arithmetic for storage and comparisons.
- **A dedicated `Money` library dependency**: unnecessary weight for the
  scope of arithmetic actually needed (parse, format, add, percent-change).
