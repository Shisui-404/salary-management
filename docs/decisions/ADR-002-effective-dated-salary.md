# ADR-002: Salary is an append-only, effective-dated timeline

## Context
HR needs a full, trustworthy history of every compensation change (raises,
promotions, corrections) for audit and review-cycle purposes. Overwriting a
`salary` column on `Employee` in place would destroy that history the moment a
raise is recorded, and would make "what did this person earn on date X"
unanswerable.

## Decision
`SalaryRecord(employee_id, amount_minor, currency, effective_from,
effective_to, change_reason, note, created_at)` is a separate, append-only
table. `Employee` has no salary column at all — it is structurally impossible
to overwrite a salary in place. The current salary is the row with
`effective_to IS NULL`. Recording a change (`services/salary_service.
record_salary_change`) does three things in one transaction: (1) validates the
new `effective_from` is strictly after the current record's, (2) sets the
current record's `effective_to = new.effective_from - 1 day`, (3) inserts the
new open record. A failed validation leaves nothing written.

## Enforcement (revised after review)
An earlier version of this ADR claimed the invariant was safe because it
"lives in exactly one function". That was not sufficient, and a code review
disproved it: two concurrent raises for the same employee could each read the
same open record before either committed, and both insert a new open row,
leaving the employee with **two** current salaries. Everything downstream then
breaks — `get_open_record`'s `scalar_one_or_none()` raises, so that employee
can never be given another raise without manual DB surgery. Single-threaded
tests could never have caught it.

The invariant is now enforced in three layers:
1. **A partial unique index** — `uq_salary_records_one_open_per_employee` on
   `(employee_id) WHERE effective_to IS NULL`. The database, not the service,
   guarantees at most one open record. Supported identically by SQLite (≥3.8.0)
   and Postgres.
2. **A row lock** — `record_salary_change` reads the open record
   `FOR UPDATE`, so on Postgres a competing raise blocks rather than racing.
   SQLite has no row-level locking and serialises write transactions instead,
   which is why layer 1 is the one that actually holds the line there.
3. **Error translation** — the resulting `IntegrityError` is caught and
   returned as `409 concurrent_salary_change`, a retryable conflict, rather
   than leaking as a 500.

Covered by `tests/api/test_salary_concurrency.py`, which forces the
interleaving with a `threading.Barrier` (deterministic, no sleeps) and
asserts that exactly one open record survives, that the loser gets a
conflict rather than a crash, and that the surviving timeline has no gap.
Removing the unique index makes three of those tests fail.

## Consequences
- Full history, "as-of" queries and audit trail fall out of the schema for free.
- The invariant (closed record's `effective_to` immediately precedes the next
  record's `effective_from`, no gaps or overlaps) is enforced by the schema and
  tested both sequentially (`tests/api/test_salary.py`) and under concurrency
  (`tests/api/test_salary_concurrency.py`).
- Every read of "current salary" is a `WHERE effective_to IS NULL` join —
  indexed (`ix_salary_records_employee_open`) and O(1) per employee.
- Callers must handle `409 concurrent_salary_change` by re-reading and
  retrying. This is the correct trade: a rejected write beats a silently
  corrupted salary history.

## Alternatives considered
- **Mutable `salary` column + a separate `salary_history` audit log**: two
  sources of truth that can drift; this design has exactly one.
- **Bitemporal versioning (valid-time + transaction-time)**: strictly more
  general, but the brief only calls for effective-dated history, not
  retroactive corrections-of-corrections with point-in-time queries against a
  prior belief state. `change_reason: "correction"` covers the realistic case.
