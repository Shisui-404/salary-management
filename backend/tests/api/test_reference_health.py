"""Tests for `GET /health` and `GET /reference`."""

from fastapi.testclient import TestClient

from tests.api.conftest import FixtureIds


def test_health_empty_db(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok", "database": "ok", "employee_count": 0}


def test_health_reflects_employee_count(client: TestClient, fixture_org: FixtureIds) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["employee_count"] == 12


def test_reference_shape_and_content(client: TestClient, fixture_org: FixtureIds) -> None:
    r = client.get("/api/v1/reference")
    assert r.status_code == 200
    body = r.json()

    assert {d["name"] for d in body["departments"]} == {"Engineering", "Sales"}
    assert {jr["name"] for jr in body["job_roles"]} == {"Software Engineer", "Sales Representative"}
    assert {lv["name"] for lv in body["levels"]} == {"L1", "L2", "L3"}
    assert {c["name"] for c in body["countries"]} == {"United States", "India"}
    assert body["base_currency"] == "USD"
    assert set(body["genders"]) == {"female", "male", "non_binary", "undisclosed"}
    assert set(body["employment_statuses"]) == {"active", "on_leave", "terminated"}
    assert "initial" in body["change_reasons"]
    assert "annual_review" in body["change_reasons"]


def test_reference_levels_carry_rank(client: TestClient, fixture_org: FixtureIds) -> None:
    r = client.get("/api/v1/reference")
    levels = {lv["name"]: lv["rank"] for lv in r.json()["levels"]}
    assert levels == {"L1": 1, "L2": 2, "L3": 3}


def test_reference_countries_carry_currency(client: TestClient, fixture_org: FixtureIds) -> None:
    r = client.get("/api/v1/reference")
    countries = {c["name"]: c["currency"] for c in r.json()["countries"]}
    assert countries == {"United States": "USD", "India": "INR"}
