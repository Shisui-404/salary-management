"""Pagination must not depend on which query path served it.

`employee_repo.get_page_rows` has two strategies: pick the page of ids from
`employees` alone and hydrate just those rows (the fast path, used whenever
the sort and filters read only employee columns), or run one fully-joined
query (used when the sort or a filter needs compensation data). Both must
return exactly the same employees in exactly the same order.

These tests also pin the OFFSET-stability property that motivated adding
`Employee.id` as a final tie-breaker: without it, rows with equal sort keys
have no defined order and paging through them can repeat or skip an employee.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FixtureIds

SORTS = [
    "name",
    "-name",
    "hire_date",
    "-hire_date",
    "department",
    "salary",
    "-salary",
    "compa_ratio",
    "-compa_ratio",
]


def _codes(client: TestClient, **params) -> list[str]:
    response = client.get("/api/v1/employees", params=params)
    assert response.status_code == 200, response.text
    return [item["employee_code"] for item in response.json()["items"]]


@pytest.mark.parametrize("sort", SORTS)
def test_paging_covers_every_employee_exactly_once(
    client: TestClient, fixture_org: FixtureIds, sort: str
) -> None:
    """Walking the pages must reconstruct the full set with no repeats or gaps."""
    total = client.get("/api/v1/employees", params={"limit": 1}).json()["total"]

    paged: list[str] = []
    for offset in range(0, total, 2):
        paged.extend(_codes(client, sort=sort, limit=2, offset=offset))

    single_page = _codes(client, sort=sort, limit=total, offset=0)

    assert len(paged) == total
    assert len(set(paged)) == total, "an employee appeared on two different pages"
    assert paged == single_page, "page-by-page order differs from the single-page order"


@pytest.mark.parametrize("sort", SORTS)
def test_sort_order_is_total_and_repeatable(
    client: TestClient, fixture_org: FixtureIds, sort: str
) -> None:
    """The same request twice must give the same order — no ties left undefined."""
    assert _codes(client, sort=sort, limit=100) == _codes(client, sort=sort, limit=100)


def test_filtered_paging_is_consistent_across_both_query_paths(
    client: TestClient, fixture_org: FixtureIds
) -> None:
    """A plain filter (fast path) and a compensation filter (joined path) must
    each stay self-consistent between a paged and an unpaged read."""
    for params in (
        {"employment_status": "active"},
        {"gender": "female"},
        {"band_position": "within"},
        {"min_salary_base": 1},
    ):
        full = _codes(client, limit=100, sort="name", **params)
        first = _codes(client, limit=2, offset=0, sort="name", **params)
        second = _codes(client, limit=2, offset=2, sort="name", **params)
        assert first + second == full[:4], f"paging inconsistent for {params}"


def test_total_matches_the_number_of_rows_actually_returned(
    client: TestClient, fixture_org: FixtureIds
) -> None:
    """`total` comes from a different query than `items` now — they must agree."""
    for params in (
        {},
        {"employment_status": "active"},
        {"band_position": "within"},
        {"search": "a"},
        {"min_salary_base": 1},
    ):
        body = client.get("/api/v1/employees", params={"limit": 100, **params}).json()
        assert body["total"] == len(body["items"]), (
            f"total {body['total']} != {len(body['items'])} items returned for {params}"
        )


def test_offset_past_the_end_returns_no_items_but_a_real_total(
    client: TestClient, fixture_org: FixtureIds
) -> None:
    body = client.get("/api/v1/employees", params={"limit": 10, "offset": 10_000}).json()
    assert body["items"] == []
    assert body["total"] > 0


@pytest.fixture
def tied_employees(client: TestClient, fixture_org: FixtureIds) -> list[str]:
    """Six employees sharing a surname AND an identical salary, so `name`,
    `salary` and `compa_ratio` all have nothing left to order them by except
    the tie-breaker."""
    codes = []
    for i in range(6):
        response = client.post(
            "/api/v1/employees",
            json={
                "first_name": f"Tied{i}",
                "last_name": "Samename",
                "email": f"tied{i}@acme.com",
                "gender": "undisclosed",
                "hire_date": "2024-01-01",
                "department_id": fixture_org.department_engineering,
                "job_role_id": fixture_org.role_swe,
                "level_id": fixture_org.level_l2,
                "country_id": fixture_org.country_us,
                "initial_salary": {"amount": "100000.00", "currency": "USD"},
            },
        )
        assert response.status_code == 201, response.text
        codes.append(response.json()["employee_code"])
    return codes


@pytest.mark.parametrize("sort", ["name", "-name", "salary", "-salary", "hire_date"])
def test_tied_sort_keys_still_page_without_repeats_or_gaps(
    client: TestClient, tied_employees: list[str], sort: str
) -> None:
    """The case the `Employee.id` tie-breaker exists for.

    Six employees share a surname, a salary and a hire date, so the requested
    sort key alone does not define a total order. A database is then free to
    return tied rows in a different sequence for each OFFSET, which makes
    paging repeat one employee and skip another.

    Honest caveat: this test passes with or without the tie-breaker today,
    because SQLite happens to return these rows in rowid order either way. It
    is pinning a guarantee, not reproducing a currently-observable failure —
    the failure is reachable on Postgres, where the planner may switch
    strategies between the two queries. It is kept because the guarantee is
    cheap and the bug it prevents is invisible until it corrupts a page.
    """
    total = client.get("/api/v1/employees", params={"limit": 1}).json()["total"]

    seen: list[str] = []
    for offset in range(total):
        seen.extend(_codes(client, sort=sort, limit=1, offset=offset))

    assert len(seen) == total
    assert len(set(seen)) == total, (
        f"paging with sort={sort} repeated an employee: "
        f"{sorted({c for c in seen if seen.count(c) > 1})}"
    )
    for code in tied_employees:
        assert code in seen, f"{code} was skipped entirely while paging"
