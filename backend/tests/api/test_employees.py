"""Tests for `GET/POST/PATCH /employees`, `GET /employees/{id}` and the
pagination/filter/sort/search contract, against the 12-employee fixture org
(see `conftest.fixture_org`).
"""

from fastapi.testclient import TestClient

from tests.api.conftest import FixtureIds


class TestListPaginationEnvelope:
    def test_default_pagination(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 12
        assert body["limit"] == 25
        assert body["offset"] == 0
        assert len(body["items"]) == 12

    def test_limit_and_offset(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?limit=5&offset=5")
        body = r.json()
        assert body["total"] == 12
        assert body["limit"] == 5
        assert body["offset"] == 5
        assert len(body["items"]) == 5

    def test_offset_past_end_returns_empty_items_but_correct_total(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees?limit=25&offset=100")
        body = r.json()
        assert body["total"] == 12
        assert body["items"] == []

    def test_limit_over_max_is_422(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?limit=101")
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"

    def test_negative_offset_is_422(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?offset=-1")
        assert r.status_code == 422

    def test_unknown_query_param_is_ignored(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees?definitely_not_a_real_param=1")
        assert r.status_code == 200
        assert r.json()["total"] == 12


class TestListFilters:
    def test_filter_by_department(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get(f"/api/v1/employees?department_id={fixture_org.department_sales}")
        body = r.json()
        assert body["total"] == 3
        assert {i["last_name"] for i in body["items"]} == {"Jones", "King", "Lee"}

    def test_filter_by_country(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get(f"/api/v1/employees?country_id={fixture_org.country_in}")
        body = r.json()
        assert body["total"] == 2
        assert {i["last_name"] for i in body["items"]} == {"Evans", "Fox"}

    def test_filter_by_level(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get(f"/api/v1/employees?level_id={fixture_org.level_l3}")
        body = r.json()
        assert body["total"] == 2
        assert {i["last_name"] for i in body["items"]} == {"Ito", "Jones"}

    def test_filter_by_gender(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?gender=female")
        assert r.json()["total"] == 6

    def test_filter_by_employment_status(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?employment_status=terminated")
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["last_name"] == "Lee"

    def test_filter_by_band_position_unbanded(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees?band_position=unbanded")
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["last_name"] == "Jones"

    def test_filter_by_band_position_above(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees?band_position=above")
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["last_name"] == "Ito"

    def test_filter_by_min_salary_base(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?min_salary_base=100000")
        body = r.json()
        # Alice(100000), Bob(110000), Dave(115000), Ivy(150000) — >= 100000 base
        assert body["total"] == 4

    def test_filter_by_salary_range(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?min_salary_base=50000&max_salary_base=90000")
        body = r.json()
        # Carol(90000), Grace(70000), Henry(75000), Jack(90000), Karen(50000), Leo(55000)
        assert body["total"] == 6

    def test_combined_filters(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get(
            f"/api/v1/employees?department_id={fixture_org.department_engineering}&gender=male"
        )
        body = r.json()
        # Bob, Dave, Frank, Henry
        assert body["total"] == 4

    def test_filter_with_no_matches_returns_empty(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees?department_id=999999")
        assert r.json() == {"items": [], "total": 0, "limit": 25, "offset": 0}

    def test_invalid_enum_filter_is_422(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?gender=not-a-gender")
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"
        assert r.json()["error"]["details"][0]["field"] == "query.gender"


class TestListSearch:
    def test_search_matches_last_name_case_insensitive(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees?search=anderson")
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["first_name"] == "Alice"

    def test_search_matches_email_substring(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees?search=bob.baker@")
        assert r.json()["total"] == 1

    def test_search_matches_employee_code(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get(f"/api/v1/employees?search=ACME-{fixture_org.alice:06d}")
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == fixture_org.alice

    def test_search_no_match(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?search=zzz-nonexistent")
        assert r.json()["total"] == 0

    def test_search_first_name_substring(self, client: TestClient, fixture_org: FixtureIds) -> None:
        # substring, not prefix -- "aro" only occurs mid-word in "Carol"
        r = client.get("/api/v1/employees?search=aro")
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["first_name"] == "Carol"


class TestListSort:
    def test_sort_by_name_ascending_default(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/employees?limit=100")
        last_names = [i["last_name"] for i in r.json()["items"]]
        assert last_names == sorted(last_names)

    def test_sort_by_name_descending(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?sort=-name&limit=100")
        last_names = [i["last_name"] for i in r.json()["items"]]
        assert last_names == sorted(last_names, reverse=True)

    def test_sort_by_hire_date_ascending(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?sort=hire_date&limit=100")
        dates = [i["hire_date"] for i in r.json()["items"]]
        assert dates == sorted(dates)
        assert dates[0] == "2018-01-01"  # Ivy, earliest hire

    def test_sort_by_salary_descending(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?sort=-salary&limit=100")
        first = r.json()["items"][0]
        assert first["last_name"] == "Ito"  # 150000 base, the highest

    def test_sort_by_salary_ascending(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?sort=salary&limit=100")
        first = r.json()["items"][0]
        assert first["last_name"] == "Evans"  # 7000 base, the lowest

    def test_sort_by_compa_ratio(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?sort=-compa_ratio&limit=100")
        items = r.json()["items"]
        # Jack is unbanded (compa_ratio null); the highest compa_ratio should
        # still surface a real, non-null value first.
        assert items[0]["compa_ratio"] is not None

    def test_sort_by_department(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees?sort=department&limit=100")
        depts = [i["department"]["name"] for i in r.json()["items"]]
        assert depts == sorted(depts)


class TestEmployeeDetail:
    def test_get_existing_employee_shape(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get(f"/api/v1/employees/{fixture_org.alice}")
        assert r.status_code == 200
        body = r.json()
        assert body["first_name"] == "Alice"
        assert body["full_name"] == "Alice Anderson"
        assert body["current_salary"]["amount"] == "100000.00"
        assert body["current_salary"]["currency"] == "USD"
        assert body["current_salary"]["amount_base"] == "100000.00"
        assert body["compa_ratio"] == 1.00
        assert body["band_position"] == "within"
        assert body["band"] == {
            "min": "85000.00",
            "mid": "100000.00",
            "max": "120000.00",
            "currency": "USD",
        }

    def test_unbanded_employee_has_null_compa_and_band(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get(f"/api/v1/employees/{fixture_org.jack}")
        body = r.json()
        assert body["compa_ratio"] is None
        assert body["band"] is None
        assert body["band_position"] == "unbanded"

    def test_indian_employee_salary_normalised_to_base(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get(f"/api/v1/employees/{fixture_org.eve}")
        body = r.json()
        assert body["current_salary"]["amount"] == "700000.00"
        assert body["current_salary"]["currency"] == "INR"
        assert body["current_salary"]["amount_base"] == "7000.00"
        assert body["current_salary"]["base_currency"] == "USD"

    def test_404_for_missing_employee(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/employees/999999")
        assert r.status_code == 404
        assert r.json() == {
            "error": {
                "code": "employee_not_found",
                "message": "Employee 999999 does not exist",
                "details": None,
            }
        }


class TestCreateEmployee:
    def _payload(self, fixture_org: FixtureIds, **overrides) -> dict:
        payload = {
            "first_name": "New",
            "last_name": "Hire",
            "email": "new.hire@acme.com",
            "gender": "female",
            "hire_date": "2024-01-01",
            "department_id": fixture_org.department_engineering,
            "job_role_id": fixture_org.role_swe,
            "level_id": fixture_org.level_l1,
            "country_id": fixture_org.country_us,
        }
        payload.update(overrides)
        return payload

    def test_create_without_salary(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.post("/api/v1/employees", json=self._payload(fixture_org))
        assert r.status_code == 201
        body = r.json()
        assert body["employee_code"].startswith("ACME-")
        assert body["current_salary"] is None
        assert (
            body["band_position"] == "unbanded"
        )  # no salary yet -> no band comparison possible...

    def test_create_with_initial_salary(self, client: TestClient, fixture_org: FixtureIds) -> None:
        payload = self._payload(
            fixture_org,
            email="salaried.hire@acme.com",
            initial_salary={"amount": "72000.00", "currency": "USD"},
        )
        r = client.post("/api/v1/employees", json=payload)
        assert r.status_code == 201
        body = r.json()
        assert body["current_salary"]["amount"] == "72000.00"
        assert body["band_position"] == "within"

        history = client.get(f"/api/v1/employees/{body['id']}/salary-history").json()
        assert len(history["items"]) == 1
        assert history["items"][0]["change_reason"] == "initial"
        assert history["items"][0]["change_pct"] is None

    def test_duplicate_email_is_409(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.post(
            "/api/v1/employees", json=self._payload(fixture_org, email="alice.anderson@acme.com")
        )
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "email_already_exists"

    def test_missing_required_field_is_422(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        payload = self._payload(fixture_org)
        del payload["email"]
        r = client.post("/api/v1/employees", json=payload)
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"

    def test_invalid_email_format_is_422(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.post("/api/v1/employees", json=self._payload(fixture_org, email="not-an-email"))
        assert r.status_code == 422

    def test_unknown_department_id_is_422(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.post("/api/v1/employees", json=self._payload(fixture_org, department_id=999999))
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"
        assert r.json()["error"]["details"][0]["field"] == "department_id"

    def test_unknown_manager_id_is_422(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.post("/api/v1/employees", json=self._payload(fixture_org, manager_id=999999))
        assert r.status_code == 422


class TestUpdateEmployee:
    def test_patch_updates_only_given_fields(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.patch(f"/api/v1/employees/{fixture_org.grace}", json={"last_name": "Greenwood"})
        assert r.status_code == 200
        body = r.json()
        assert body["last_name"] == "Greenwood"
        assert body["first_name"] == "Grace"  # untouched

    def test_patch_cannot_change_salary_fields(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        # There is no salary field accepted by the schema at all; sending one
        # should be silently ignored (extra fields are not part of EmployeeUpdate).
        r = client.patch(
            f"/api/v1/employees/{fixture_org.grace}", json={"current_salary": {"amount": "1.00"}}
        )
        assert r.status_code == 200
        # salary is unaffected
        detail = client.get(f"/api/v1/employees/{fixture_org.grace}").json()
        assert detail["current_salary"]["amount"] == "70000.00"

    def test_patch_404_for_missing_employee(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.patch("/api/v1/employees/999999", json={"last_name": "X"})
        assert r.status_code == 404

    def test_patch_duplicate_email_is_409(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.patch(
            f"/api/v1/employees/{fixture_org.grace}", json={"email": "alice.anderson@acme.com"}
        )
        assert r.status_code == 409

    def test_patch_own_email_unchanged_is_not_a_conflict(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.patch(
            f"/api/v1/employees/{fixture_org.grace}", json={"email": "grace.green@acme.com"}
        )
        assert r.status_code == 200

    def test_patch_self_as_manager_is_422(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.patch(
            f"/api/v1/employees/{fixture_org.grace}", json={"manager_id": fixture_org.grace}
        )
        assert r.status_code == 422

    def test_patch_reassign_manager(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.patch(
            f"/api/v1/employees/{fixture_org.grace}", json={"manager_id": fixture_org.alice}
        )
        assert r.status_code == 200
        assert r.json()["manager_id"] == fixture_org.alice
