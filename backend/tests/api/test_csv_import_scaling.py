"""CSV import must not issue a query per row for static reference data.

Bulk-loading off a spreadsheet is an explicit job-to-be-done (requirements
J6), so the import path has to scale with the size of the file. Departments,
job roles, levels and countries are small static tables; resolving them per
row cost four queries per row, which is 40,000 queries for a 10,000-row
import before counting the per-row employee lookups.

This test counts actual SQL statements rather than asserting on timing, so it
is deterministic and does not depend on machine speed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from tests.api.conftest import FixtureIds

HEADER = (
    "first_name,last_name,email,gender,hire_date,employment_status,"
    "department,job_role,level,country\n"
)


def _csv(rows: int) -> bytes:
    body = "".join(
        f"Imported,Person{i},imported{i}@acme.com,undisclosed,2025-01-15,active,"
        f"Engineering,Software Engineer,L2,United States\n"
        for i in range(rows)
    )
    return (HEADER + body).encode()


REFERENCE_TABLES = ("departments", "job_roles", "levels", "countries")


@pytest.fixture
def recorded_statements(db_session: Session):
    """Every SQL statement issued, so tests can assert on query *shape* rather
    than on timing (deterministic, machine-independent)."""
    statements: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(" ".join(statement.split()))

    event.listen(db_session.bind, "before_cursor_execute", before_cursor_execute)
    yield statements
    event.remove(db_session.bind, "before_cursor_execute", before_cursor_execute)


def _reference_reads(statements: list[str]) -> int:
    return sum(
        1
        for stmt in statements
        if stmt.upper().startswith("SELECT")
        and any(f" FROM {table}" in stmt for table in REFERENCE_TABLES)
    )


def _import(client: TestClient, rows: int) -> dict:
    response = client.post(
        "/api/v1/employees/import",
        files={"file": ("people.csv", _csv(rows), "text/csv")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_reference_tables_are_read_a_fixed_number_of_times(
    client: TestClient, fixture_org: FixtureIds, recorded_statements: list[str]
) -> None:
    """The four static reference tables are read once each per import, no
    matter how many rows the file has.

    Before the fix this was four reads *per row*. The import still does its
    own per-row work (an existence check, the insert, the employee-code
    update) -- that part is inherent to row-by-row upsert semantics and is not
    what this test constrains.
    """
    recorded_statements.clear()
    _import(client, 5)
    reads_for_5 = _reference_reads(recorded_statements)

    recorded_statements.clear()
    _import(client, 25)
    reads_for_25 = _reference_reads(recorded_statements)

    assert reads_for_5 == reads_for_25, (
        f"reference tables read {reads_for_5} times for 5 rows but {reads_for_25} "
        "times for 25 -- they are being re-read per row"
    )
    assert reads_for_25 <= len(REFERENCE_TABLES), (
        f"expected at most one read per reference table, got {reads_for_25}"
    )


def test_import_still_reports_per_row_errors_after_caching(
    client: TestClient, fixture_org: FixtureIds
) -> None:
    """The cache must not change the error contract: unknown names still fail
    their own row, by field, without stopping the rest of the file."""
    csv_bytes = (
        HEADER + "Good,Row,good.row@acme.com,female,2025-01-15,active,"
        "Engineering,Software Engineer,L2,United States\n"
        + "Bad,Dept,bad.dept@acme.com,male,2025-01-15,active,"
        "Nonexistent,Software Engineer,L2,United States\n"
        + "Bad,Role,bad.role@acme.com,male,2025-01-15,active,"
        "Engineering,Nonexistent Role,L2,United States\n"
    ).encode()

    body = client.post(
        "/api/v1/employees/import", files={"file": ("people.csv", csv_bytes, "text/csv")}
    ).json()

    assert body["total_rows"] == 3
    assert body["created"] == 1
    assert body["failed"] == 2
    fields = {(e["row"], e["field"]) for e in body["errors"]}
    assert (2, "department") in fields
    assert (3, "job_role") in fields


def test_reference_names_match_case_insensitively(
    client: TestClient, fixture_org: FixtureIds
) -> None:
    """The cache is keyed on casefolded names, matching what the per-row
    queries did for the names an HR manager actually types."""
    csv_bytes = (
        HEADER + "Case,Insensitive,case.insensitive@acme.com,female,2025-01-15,active,"
        "ENGINEERING,software engineer,l2,united states\n"
    ).encode()

    body = client.post(
        "/api/v1/employees/import", files={"file": ("people.csv", csv_bytes, "text/csv")}
    ).json()

    assert body["failed"] == 0, body["errors"]
    assert body["created"] == 1
