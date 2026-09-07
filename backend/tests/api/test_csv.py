"""Tests for `GET /employees/export` and `POST /employees/import`."""

import csv
import io

from fastapi.testclient import TestClient

from tests.api.conftest import FixtureIds


class TestExport:
    def test_export_is_csv_with_header_and_every_employee(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees/export")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert "attachment" in r.headers["content-disposition"]

        rows = list(csv.DictReader(io.StringIO(r.text)))
        assert len(rows) == 12
        assert {row["last_name"] for row in rows} == {
            "Anderson",
            "Baker",
            "Chen",
            "Diaz",
            "Evans",
            "Fox",
            "Green",
            "Hall",
            "Ito",
            "Jones",
            "King",
            "Lee",
        }

    def test_export_respects_filters(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get(f"/api/v1/employees/export?department_id={fixture_org.department_sales}")
        rows = list(csv.DictReader(io.StringIO(r.text)))
        assert len(rows) == 3

    def test_export_money_is_decimal_string_not_scientific_notation(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees/export")
        rows = list(csv.DictReader(io.StringIO(r.text)))
        alice_row = next(row for row in rows if row["last_name"] == "Anderson")
        assert alice_row["salary_amount"] == "100000.00"
        assert alice_row["salary_amount_base"] == "100000.00"

    def test_export_empty_org(self, client: TestClient) -> None:
        r = client.get("/api/v1/employees/export")
        assert r.status_code == 200
        rows = list(csv.DictReader(io.StringIO(r.text)))
        assert rows == []


VALID_HEADER = (
    "first_name,last_name,email,gender,hire_date,employment_status,"
    "department,job_role,level,country,salary_amount,salary_currency\n"
)


class TestImport:
    def test_import_happy_path_creates_employees(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        csv_content = VALID_HEADER + (
            "Nina,Novak,nina.novak@acme.com,female,2024-01-01,active,"
            "Engineering,Software Engineer,L1,United States,72000.00,USD\n"
        )
        r = client.post(
            "/api/v1/employees/import",
            files={"file": ("import.csv", csv_content.encode(), "text/csv")},
        )
        assert r.status_code == 200
        body = r.json()
        assert body == {"total_rows": 1, "created": 1, "updated": 0, "failed": 0, "errors": []}

        listing = client.get("/api/v1/employees?search=novak").json()
        assert listing["total"] == 1
        assert listing["items"][0]["current_salary"]["amount"] == "72000.00"

    def test_import_updates_existing_employee_matched_by_email(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        csv_content = VALID_HEADER + (
            "Grace,Greenwood,grace.green@acme.com,female,2022-01-01,active,"
            "Engineering,Software Engineer,L1,United States,,\n"
        )
        r = client.post(
            "/api/v1/employees/import",
            files={"file": ("import.csv", csv_content.encode(), "text/csv")},
        )
        body = r.json()
        assert body == {"total_rows": 1, "created": 0, "updated": 1, "failed": 0, "errors": []}

        detail = client.get(f"/api/v1/employees/{fixture_org.grace}").json()
        assert detail["last_name"] == "Greenwood"
        # salary is untouched by import -- still the original 70000.00
        assert detail["current_salary"]["amount"] == "70000.00"

    def test_import_reports_per_row_errors_and_applies_valid_rows(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        csv_content = VALID_HEADER + (
            "Valid,Row,valid.row@acme.com,female,2024-01-01,active,"
            "Engineering,Software Engineer,L1,United States,,\n"
            ",MissingFirstName,missing@acme.com,female,2024-01-01,active,"
            "Engineering,Software Engineer,L1,United States,,\n"
            "Bad,Gender,bad.gender@acme.com,not-a-gender,2024-01-01,active,"
            "Engineering,Software Engineer,L1,United States,,\n"
            "Unknown,Dept,unknown.dept@acme.com,male,2024-01-01,active,"
            "NoSuchDept,Software Engineer,L1,United States,,\n"
        )
        r = client.post(
            "/api/v1/employees/import",
            files={"file": ("import.csv", csv_content.encode(), "text/csv")},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total_rows"] == 4
        assert body["created"] == 1
        assert body["updated"] == 0
        assert body["failed"] == 3
        assert len(body["errors"]) == 3

        error_rows = {e["row"] for e in body["errors"]}
        assert error_rows == {2, 3, 4}
        fields_by_row = {e["row"]: e["field"] for e in body["errors"]}
        assert fields_by_row[2] == "first_name"
        assert fields_by_row[3] == "gender"
        assert fields_by_row[4] == "department"

        # the one valid row was still applied despite the other three failing
        listing = client.get("/api/v1/employees?search=valid.row").json()
        assert listing["total"] == 1

    def test_import_empty_file_is_a_no_op(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.post(
            "/api/v1/employees/import",
            files={"file": ("empty.csv", VALID_HEADER.encode(), "text/csv")},
        )
        assert r.status_code == 200
        assert r.json() == {"total_rows": 0, "created": 0, "updated": 0, "failed": 0, "errors": []}

    def test_import_row_with_only_amount_no_currency_is_rejected(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        csv_content = VALID_HEADER + (
            "Partial,Salary,partial.salary@acme.com,male,2024-01-01,active,"
            "Engineering,Software Engineer,L1,United States,50000.00,\n"
        )
        r = client.post(
            "/api/v1/employees/import",
            files={"file": ("import.csv", csv_content.encode(), "text/csv")},
        )
        body = r.json()
        assert body["failed"] == 1
        assert body["errors"][0]["field"] == "salary_amount"
