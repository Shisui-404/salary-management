"""Tests for the effective-dated salary revision invariant:
`POST /employees/{id}/salary` and `GET /employees/{id}/salary-history`.

These are the highest-value tests in the suite -- the domain brief's core
non-negotiable is "salary is append-only and effective-dated, never
overwritten in place".
"""

import itertools

from fastapi.testclient import TestClient

from tests.api.conftest import FixtureIds


class TestRecordSalaryChange:
    def test_raise_closes_prior_record_and_opens_new_one(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "80000.00",
                "currency": "USD",
                "effective_from": "2023-01-01",
                "change_reason": "annual_review",
                "note": "Strong year",
            },
        )
        assert r.status_code == 201
        new_record = r.json()
        assert new_record["amount"] == "80000.00"
        assert new_record["effective_to"] is None
        assert new_record["change_reason"] == "annual_review"
        assert new_record["note"] == "Strong year"
        # 80000 vs previous 70000 -> +14.3%
        assert new_record["change_pct"] == 14.3

        history = client.get(f"/api/v1/employees/{fixture_org.grace}/salary-history").json()[
            "items"
        ]
        assert len(history) == 2
        # newest first
        assert history[0]["amount"] == "80000.00"
        assert history[0]["effective_to"] is None
        assert history[1]["amount"] == "70000.00"
        assert history[1]["effective_to"] == "2022-12-31"  # day before the new effective_from
        assert history[1]["change_pct"] is None  # first record ever

    def test_current_salary_on_employee_reflects_latest_record(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "82000.00",
                "currency": "USD",
                "effective_from": "2023-01-01",
                "change_reason": "promotion",
            },
        )
        detail = client.get(f"/api/v1/employees/{fixture_org.grace}").json()
        assert detail["current_salary"]["amount"] == "82000.00"
        assert detail["current_salary"]["change_reason"] == "promotion"

    def test_multiple_raises_build_full_history_in_order(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "75000.00",
                "currency": "USD",
                "effective_from": "2023-01-01",
                "change_reason": "annual_review",
            },
        )
        client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "85000.00",
                "currency": "USD",
                "effective_from": "2024-01-01",
                "change_reason": "promotion",
            },
        )
        history = client.get(f"/api/v1/employees/{fixture_org.grace}/salary-history").json()[
            "items"
        ]
        amounts = [item["amount"] for item in history]
        assert amounts == ["85000.00", "75000.00", "70000.00"]
        froms = [item["effective_from"] for item in history]
        assert froms == ["2024-01-01", "2023-01-01", "2022-01-01"]

    def test_effective_to_chain_has_no_gaps_or_overlaps(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "75000.00",
                "currency": "USD",
                "effective_from": "2023-01-01",
                "change_reason": "annual_review",
            },
        )
        client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "85000.00",
                "currency": "USD",
                "effective_from": "2024-01-01",
                "change_reason": "promotion",
            },
        )
        history = client.get(f"/api/v1/employees/{fixture_org.grace}/salary-history").json()[
            "items"
        ]
        # oldest -> newest
        chronological = list(reversed(history))
        for earlier, later in itertools.pairwise(chronological):
            assert earlier["effective_to"] is not None
            assert earlier["effective_to"] < later["effective_from"]

    def test_backdated_effective_from_is_rejected(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        # Grace's current record started 2022-01-01; anything on/before that is invalid.
        r = client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "80000.00",
                "currency": "USD",
                "effective_from": "2021-01-01",
                "change_reason": "correction",
            },
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "salary_effective_date_invalid"

    def test_same_day_effective_from_is_rejected(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "80000.00",
                "currency": "USD",
                "effective_from": "2022-01-01",  # exactly the current record's effective_from
                "change_reason": "correction",
            },
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "salary_effective_date_invalid"

    def test_rejected_revision_does_not_mutate_history(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        before = client.get(f"/api/v1/employees/{fixture_org.grace}/salary-history").json()
        r = client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "1.00",
                "currency": "USD",
                "effective_from": "2020-01-01",
                "change_reason": "correction",
            },
        )
        assert r.status_code == 422
        after = client.get(f"/api/v1/employees/{fixture_org.grace}/salary-history").json()
        assert before == after

    def test_404_for_missing_employee(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.post(
            "/api/v1/employees/999999/salary",
            json={
                "amount": "80000.00",
                "currency": "USD",
                "effective_from": "2023-01-01",
                "change_reason": "annual_review",
            },
        )
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "employee_not_found"

    def test_invalid_change_reason_is_422(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "80000.00",
                "currency": "USD",
                "effective_from": "2023-01-01",
                "change_reason": "bonus",  # not one of the allowed enum values
            },
        )
        assert r.status_code == 422

    def test_invalid_currency_is_422(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "80000.00",
                "currency": "US",  # not 3 letters
                "effective_from": "2023-01-01",
                "change_reason": "annual_review",
            },
        )
        assert r.status_code == 422

    def test_negative_amount_is_422(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.post(
            f"/api/v1/employees/{fixture_org.grace}/salary",
            json={
                "amount": "-1.00",
                "currency": "USD",
                "effective_from": "2023-01-01",
                "change_reason": "correction",
            },
        )
        assert r.status_code == 422

    def test_currency_can_change_between_records_and_breaks_change_pct(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        # Eve started in INR; a relocation-driven raise in USD shouldn't
        # produce a nonsensical cross-currency percentage.
        r = client.post(
            f"/api/v1/employees/{fixture_org.eve}/salary",
            json={
                "amount": "9000.00",
                "currency": "USD",
                "effective_from": "2023-01-01",
                "change_reason": "role_change",
            },
        )
        assert r.status_code == 201
        assert r.json()["change_pct"] is None


class TestSalaryHistoryEndpoint:
    def test_history_for_employee_with_single_record(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get(f"/api/v1/employees/{fixture_org.alice}/salary-history")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["change_reason"] == "initial"
        assert items[0]["change_pct"] is None
        assert items[0]["effective_to"] is None

    def test_history_404_for_missing_employee(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees/999999/salary-history")
        assert r.status_code == 404
