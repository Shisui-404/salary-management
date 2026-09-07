"""Unit tests for `app.services.csv_io.validate_row` — pure field-shape
validation for one CSV row, no database access. Reference-name resolution
(department/job-role/level/country -> id) and the upsert orchestration are
DB-dependent and covered by `tests/api/test_csv.py` instead.
"""

import pytest

from app.services.csv_io import IMPORT_REQUIRED_FIELDS, validate_row

VALID_ROW = {
    "first_name": "Ada",
    "last_name": "Lovelace",
    "email": "ada@acme.com",
    "gender": "female",
    "hire_date": "2021-04-01",
    "employment_status": "active",
    "department": "Engineering",
    "job_role": "Software Engineer",
    "level": "L3",
    "country": "India",
}


class TestValidateRowHappyPath:
    def test_fully_valid_row_parses(self) -> None:
        parsed, errors = validate_row(VALID_ROW, row_number=1)
        assert errors == []
        assert parsed is not None
        assert parsed.first_name == "Ada"
        assert parsed.gender.value == "female"
        assert parsed.hire_date.isoformat() == "2021-04-01"

    def test_employment_status_defaults_to_active_when_omitted(self) -> None:
        row = {k: v for k, v in VALID_ROW.items() if k != "employment_status"}
        parsed, errors = validate_row(row, row_number=1)
        assert errors == []
        assert parsed.employment_status.value == "active"

    def test_optional_salary_pair_accepted_together(self) -> None:
        row = {**VALID_ROW, "salary_amount": "2400000.00", "salary_currency": "inr"}
        parsed, errors = validate_row(row, row_number=1)
        assert errors == []
        assert parsed.salary_amount == "2400000.00"
        assert parsed.salary_currency == "INR"

    def test_optional_fields_omitted_entirely_is_valid(self) -> None:
        parsed, errors = validate_row(VALID_ROW, row_number=1)
        assert errors == []
        assert parsed.employee_code is None
        assert parsed.manager_employee_code is None
        assert parsed.salary_amount is None


class TestValidateRowRequiredFields:
    @pytest.mark.parametrize("field", IMPORT_REQUIRED_FIELDS)
    def test_missing_required_field_is_reported(self, field: str) -> None:
        row = {**VALID_ROW, field: ""}
        parsed, errors = validate_row(row, row_number=7)
        assert parsed is None
        assert any(e.field == field and e.row == 7 for e in errors)

    def test_whitespace_only_field_counts_as_missing(self) -> None:
        row = {**VALID_ROW, "first_name": "   "}
        parsed, errors = validate_row(row, row_number=1)
        assert parsed is None
        assert any(e.field == "first_name" for e in errors)

    def test_multiple_missing_fields_all_reported(self) -> None:
        row = {**VALID_ROW, "first_name": "", "email": ""}
        _parsed, errors = validate_row(row, row_number=1)
        fields = {e.field for e in errors}
        assert {"first_name", "email"} <= fields


class TestValidateRowFieldFormats:
    @pytest.mark.parametrize(
        "bad_email", ["not-an-email", "no-domain@", "@nodomain.com", "plaintext"]
    )
    def test_invalid_email_rejected(self, bad_email: str) -> None:
        row = {**VALID_ROW, "email": bad_email}
        parsed, errors = validate_row(row, row_number=1)
        assert parsed is None
        assert any(e.field == "email" for e in errors)

    def test_invalid_gender_rejected(self) -> None:
        row = {**VALID_ROW, "gender": "robot"}
        parsed, errors = validate_row(row, row_number=1)
        assert parsed is None
        assert any(e.field == "gender" for e in errors)

    def test_invalid_hire_date_rejected(self) -> None:
        row = {**VALID_ROW, "hire_date": "04/01/2021"}
        parsed, errors = validate_row(row, row_number=1)
        assert parsed is None
        assert any(e.field == "hire_date" for e in errors)

    def test_invalid_employment_status_rejected(self) -> None:
        row = {**VALID_ROW, "employment_status": "retired"}
        parsed, errors = validate_row(row, row_number=1)
        assert parsed is None
        assert any(e.field == "employment_status" for e in errors)


class TestValidateRowSalaryPair:
    def test_amount_without_currency_is_rejected(self) -> None:
        row = {**VALID_ROW, "salary_amount": "1000.00"}
        parsed, errors = validate_row(row, row_number=1)
        assert parsed is None
        assert any(e.field == "salary_amount" for e in errors)

    def test_currency_without_amount_is_rejected(self) -> None:
        row = {**VALID_ROW, "salary_currency": "USD"}
        parsed, errors = validate_row(row, row_number=1)
        assert parsed is None
        assert any(e.field == "salary_amount" for e in errors)

    def test_invalid_amount_is_rejected(self) -> None:
        row = {**VALID_ROW, "salary_amount": "not-a-number", "salary_currency": "USD"}
        parsed, errors = validate_row(row, row_number=1)
        assert parsed is None
        assert any(e.field == "salary_amount" for e in errors)

    def test_invalid_currency_is_rejected(self) -> None:
        row = {**VALID_ROW, "salary_amount": "1000.00", "salary_currency": "US"}
        parsed, errors = validate_row(row, row_number=1)
        assert parsed is None
        assert any(e.field == "salary_currency" for e in errors)


class TestValidateRowErrorAccumulation:
    def test_multiple_field_errors_all_reported_in_one_pass(self) -> None:
        row = {
            **VALID_ROW,
            "gender": "bogus",
            "hire_date": "not-a-date",
            "email": "bad",
        }
        parsed, errors = validate_row(row, row_number=3)
        assert parsed is None
        fields = {e.field for e in errors}
        assert {"gender", "hire_date", "email"} <= fields
        assert all(e.row == 3 for e in errors)
