"""Tests for the five `/analytics/*` endpoints against the 12-employee
fixture org (`conftest.fixture_org`).

Every expected number below is worked out by hand from the fixture's raw
inputs (see `conftest.py`) so these are exact-value assertions, not just
shape checks. The fixture, restated in base-currency (USD) annual salary,
sorted ascending:

    Eve     7,000.00   (India, SWE L2 -- 700,000 INR @ 0.01)
    Frank   7,500.00   (India, SWE L2 -- 750,000 INR @ 0.01)
    Karen  50,000.00   (US, Sales Rep L1)
    Leo    55,000.00   (US, Sales Rep L1)   [terminated]
    Grace  70,000.00   (US, SWE L1)
    Henry  75,000.00   (US, SWE L1)
    Jack   90,000.00   (US, Sales Rep L3 -- no band defined -> unbanded)
    Carol  90,000.00   (US, SWE L2)
    Alice 100,000.00   (US, SWE L2)
    Bob   110,000.00   (US, SWE L2)
    Dave  115,000.00   (US, SWE L2)
    Ivy   150,000.00   (US, SWE L3 -- band max 145,000 -> above/outlier) [on_leave]

n=12. sum=919,500.00. mean=76,625.00 (exact). median (avg of the 6th/7th
sorted values, i.e. average of 75,000 and 90,000)=82,500.00.
percentile_cont ranks (p * (n-1) = p * 11): p10 rank=1.1 -> between Frank
(idx1=7,500) and Karen (idx2=50,000) -> 11,750.00. p25 rank=2.75 -> between
Karen (50,000) and Leo (55,000) -> 53,750.00. p75 rank=8.25 -> between Alice
(idx8=100,000) and Bob (idx9=110,000) -> 102,500.00. p90 rank=9.9 -> between
Bob (110,000) and Dave (115,000) -> 114,500.00.

6 female (Alice, Carol, Eve, Grace, Ivy, Karen), 6 male (Bob, Dave, Frank,
Henry, Jack, Leo). Every (job_role, level) cell has at most 3 people on
either gender side, so at the contract's default `min_sample_size=5`, every
group is suppressed -- exercising the small-sample guard end to end.
"""

from fastapi.testclient import TestClient

from tests.api.conftest import FixtureIds


class TestSummary:
    def test_exact_values(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/summary")
        assert r.status_code == 200
        assert r.json() == {
            "base_currency": "USD",
            "headcount": 12,
            "active_headcount": 10,
            "total_annual_payroll": "919500.00",
            "mean_salary": "76625.00",
            "median_salary": "82500.00",
            "min_salary": "7000.00",
            "max_salary": "150000.00",
            "countries": 2,
            "departments": 2,
            "band_coverage_pct": 91.7,
        }

    def test_filtered_by_department(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get(f"/api/v1/analytics/summary?department_id={fixture_org.department_sales}")
        body = r.json()
        assert body["headcount"] == 3
        assert body["total_annual_payroll"] == "195000.00"

    def test_empty_result_set(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/summary?department_id=999999")
        body = r.json()
        assert body["headcount"] == 0
        assert body["total_annual_payroll"] == "0.00"
        assert body["median_salary"] == "0.00"
        assert body["band_coverage_pct"] == 0.0

    def test_no_fixture_data_at_all(self, client: TestClient) -> None:
        r = client.get("/api/v1/analytics/summary")
        assert r.status_code == 200
        assert r.json()["headcount"] == 0


class TestDistribution:
    def test_exact_percentiles(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/distribution")
        assert r.status_code == 200
        assert r.json()["percentiles"] == {
            "p10": "11750.00",
            "p25": "53750.00",
            "p50": "82500.00",
            "p75": "102500.00",
            "p90": "114500.00",
        }

    def test_histogram_bucket_count_default(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/analytics/distribution")
        assert len(r.json()["histogram"]) == 12

    def test_histogram_bucket_count_param(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/analytics/distribution?buckets=6")
        assert len(r.json()["histogram"]) == 6

    def test_histogram_covers_every_employee(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/analytics/distribution?buckets=5")
        total = sum(b["count"] for b in r.json()["histogram"])
        assert total == 12

    def test_buckets_out_of_range_is_422(self, client: TestClient, fixture_org: FixtureIds) -> None:
        assert client.get("/api/v1/analytics/distribution?buckets=4").status_code == 422
        assert client.get("/api/v1/analytics/distribution?buckets=31").status_code == 422

    def test_empty_result_set_has_empty_histogram(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/analytics/distribution?department_id=999999")
        assert r.json()["histogram"] == []


class TestByDimension:
    def test_department_exact_values(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/by-dimension?dimension=department")
        assert r.status_code == 200
        body = r.json()
        assert body["dimension"] == "department"
        groups = {g["name"]: g for g in body["groups"]}
        assert groups["Engineering"]["headcount"] == 9
        assert groups["Engineering"]["median"] == "90000.00"
        assert groups["Engineering"]["mean"] == "80500.00"
        assert groups["Engineering"]["p25"] == "70000.00"
        assert groups["Engineering"]["p75"] == "110000.00"
        assert groups["Engineering"]["min"] == "7000.00"
        assert groups["Engineering"]["max"] == "150000.00"
        assert groups["Engineering"]["total_payroll"] == "724500.00"

        assert groups["Sales"]["headcount"] == 3
        assert groups["Sales"]["median"] == "55000.00"
        assert groups["Sales"]["mean"] == "65000.00"
        assert groups["Sales"]["p25"] == "52500.00"
        assert groups["Sales"]["p75"] == "72500.00"
        assert groups["Sales"]["total_payroll"] == "195000.00"

    def test_sorted_by_headcount_desc(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/by-dimension?dimension=department")
        names = [g["name"] for g in r.json()["groups"]]
        assert names == ["Engineering", "Sales"]

    def test_country_dimension(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/by-dimension?dimension=country")
        groups = {g["name"]: g["headcount"] for g in r.json()["groups"]}
        assert groups == {"United States": 10, "India": 2}

    def test_missing_dimension_is_422(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/by-dimension")
        assert r.status_code == 422

    def test_invalid_dimension_is_422(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/by-dimension?dimension=not-a-real-dimension")
        assert r.status_code == 422


class TestPayEquity:
    def test_overall_exact_values(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/pay-equity")
        assert r.status_code == 200
        body = r.json()
        assert body["base_currency"] == "USD"
        assert body["min_sample_size"] == 5
        assert body["overall"] == {
            "reference": "male",
            "comparison": "female",
            "reference_median": "82500.00",
            "comparison_median": "80000.00",
            "gap_pct": 3.0,
            "sample_reference": 6,
            "sample_comparison": 6,
        }

    def test_default_sample_size_suppresses_every_small_group(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/analytics/pay-equity")
        body = r.json()
        assert body["groups"] == []
        assert body["suppressed_groups"] == 5

    def test_lower_sample_size_unsuppresses_the_largest_group(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        r = client.get("/api/v1/analytics/pay-equity?min_sample_size=2")
        body = r.json()
        assert body["min_sample_size"] == 2
        assert len(body["groups"]) == 1
        group = body["groups"][0]
        assert group["key"] == "Software Engineer · L2"
        assert group["job_role"] == "Software Engineer"
        assert group["level"] == "L2"
        assert group["reference_median"] == "110000.00"
        assert group["comparison_median"] == "90000.00"
        assert group["gap_pct"] == 18.2
        assert group["sample_reference"] == 3
        assert group["sample_comparison"] == 3
        assert group["sufficient_sample"] is True
        assert body["suppressed_groups"] == 4

    def test_min_sample_size_out_of_range_is_422(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        assert client.get("/api/v1/analytics/pay-equity?min_sample_size=0").status_code == 422

    def test_no_data_returns_null_overall(self, client: TestClient) -> None:
        r = client.get("/api/v1/analytics/pay-equity")
        assert r.status_code == 200
        assert r.json()["overall"] is None
        assert r.json()["groups"] == []


class TestBandHealth:
    def test_exact_counts(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/band-health")
        assert r.status_code == 200
        body = r.json()
        assert body["below"] == 0
        assert body["within"] == 10
        assert body["above"] == 1
        assert body["unbanded"] == 1
        assert body["below_pct"] == 0.0
        assert body["within_pct"] == 83.3
        assert body["above_pct"] == 8.3

    def test_outlier_is_ivy_above_band(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/band-health")
        outliers = r.json()["outliers"]
        assert len(outliers) == 1
        outlier = outliers[0]
        assert outlier["full_name"] == "Ivy Ito"
        assert outlier["department"] == "Engineering"
        assert outlier["job_role"] == "Software Engineer"
        assert outlier["level"] == "L3"
        assert outlier["country"] == "US"
        assert outlier["salary_base"] == "150000.00"
        assert outlier["band_min"] == "110000.00"
        assert outlier["band_max"] == "145000.00"
        assert outlier["compa_ratio"] == 1.2
        assert outlier["position"] == "above"
        assert outlier["deviation_pct"] == 3.4

    def test_outliers_capped_at_20(self, client: TestClient, fixture_org: FixtureIds) -> None:
        r = client.get("/api/v1/analytics/band-health")
        assert len(r.json()["outliers"]) <= 20

    def test_empty_db(self, client: TestClient) -> None:
        r = client.get("/api/v1/analytics/band-health")
        body = r.json()
        assert body["below"] == body["within"] == body["above"] == body["unbanded"] == 0
        assert body["outliers"] == []


class TestAnalyticsShareFiltersWithEmployeeList:
    def test_filters_narrow_every_endpoint_consistently(
        self, client: TestClient, fixture_org: FixtureIds
    ) -> None:
        params = f"country_id={fixture_org.country_in}"
        employees = client.get(f"/api/v1/employees?{params}").json()
        summary = client.get(f"/api/v1/analytics/summary?{params}").json()
        assert employees["total"] == summary["headcount"] == 2
