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

## Consequences
- Full history, "as-of" queries and audit trail fall out of the schema for free.
- The invariant (closed record's `effective_to` immediately precedes the next
  record's `effective_from`, no gaps or overlaps) lives in exactly one
  function and is heavily tested (`tests/api/test_salary.py`).
- Every read of "current salary" is a `WHERE effective_to IS NULL` join —
  indexed (`ix_salary_records_employee_open`) and O(1) per employee.

## Alternatives considered
- **Mutable `salary` column + a separate `salary_history` audit log**: two
  sources of truth that can drift; this design has exactly one.
- **Bitemporal versioning (valid-time + transaction-time)**: strictly more
  general, but the brief only calls for effective-dated history, not
  retroactive corrections-of-corrections with point-in-time queries against a
  prior belief state. `change_reason: "correction"` covers the realistic case.
