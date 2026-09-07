# API Contract v1 — binding for both backend and frontend

Base URL: `/api/v1`. Content type: `application/json`.
**This document is the source of truth.** Backend implements it exactly; frontend codes against
it exactly. Neither side changes it unilaterally.

## Conventions

- **Money is never a JSON number.** Amounts are decimal **strings**: `"2400000.00"`.
  Internally stored as integer minor units + ISO-4217 code.
- Dates are `YYYY-MM-DD` strings. Timestamps are ISO-8601 UTC.
- Base currency for all normalised/comparison figures: `USD` (configurable, echoed in responses).
- All salary amounts are **annual gross base salary**.
- Unknown query params are ignored; invalid ones return 422.

### Pagination envelope
```json
{ "items": [ ... ], "total": 10000, "limit": 25, "offset": 0 }
```
`limit` default 25, max 100. `offset` default 0.

### Error shape (all 4xx/5xx)
```json
{ "error": { "code": "employee_not_found", "message": "Employee 42 does not exist", "details": null } }
```
Validation failures use `code: "validation_error"` with
`details: [ { "field": "email", "message": "..." } ]`.

## Shared objects

### `Money`
```json
{ "amount": "2400000.00", "currency": "INR" }
```

### `RefItem`
```json
{ "id": 3, "name": "Engineering" }
```
For level: `{ "id": 2, "name": "L3", "rank": 3 }`.
For country: `{ "id": 1, "name": "India", "code": "IN", "currency": "INR" }`.

### `CurrentSalary`
```json
{
  "amount": "2400000.00",
  "currency": "INR",
  "amount_base": "28800.00",
  "base_currency": "USD",
  "effective_from": "2024-04-01",
  "change_reason": "annual_review"
}
```
`null` when the employee has no salary record.

### `Employee`
```json
{
  "id": 1,
  "employee_code": "ACME-000001",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "full_name": "Ada Lovelace",
  "email": "ada.lovelace@acme.com",
  "gender": "female",
  "hire_date": "2021-04-01",
  "employment_status": "active",
  "department": { "id": 3, "name": "Engineering" },
  "job_role": { "id": 5, "name": "Software Engineer" },
  "level": { "id": 2, "name": "L3", "rank": 3 },
  "country": { "id": 1, "name": "India", "code": "IN", "currency": "INR" },
  "manager_id": 7,
  "current_salary": { "...CurrentSalary..." },
  "compa_ratio": 0.98,
  "band_position": "within",
  "band": { "min": "20000.00", "mid": "29000.00", "max": "38000.00", "currency": "USD" }
}
```
`band_position` ∈ `"below" | "within" | "above" | "unbanded"`.
`compa_ratio` is `null` when unbanded. `gender` ∈ `"female" | "male" | "non_binary" | "undisclosed"`.
`employment_status` ∈ `"active" | "on_leave" | "terminated"`.

### `SalaryRecord`
```json
{
  "id": 900,
  "employee_id": 1,
  "amount": "2400000.00",
  "currency": "INR",
  "amount_base": "28800.00",
  "base_currency": "USD",
  "effective_from": "2024-04-01",
  "effective_to": null,
  "change_reason": "annual_review",
  "note": "Strong performance",
  "created_at": "2024-03-15T09:00:00Z",
  "change_pct": 12.5
}
```
`change_pct` is the increase over the immediately preceding record in local currency
(`null` for the first record).
`change_reason` ∈ `"initial" | "annual_review" | "promotion" | "market_adjustment" | "role_change" | "correction"`.

---

## Endpoints

### `GET /employees`
Query: `search`, `department_id`, `country_id`, `job_role_id`, `level_id`,
`employment_status`, `gender`, `band_position`, `min_salary_base`, `max_salary_base`,
`sort` (`name|salary|hire_date|compa_ratio|department`, prefix `-` for desc, default `name`),
`limit`, `offset`.
`search` matches first name, last name, email or employee code, case-insensitive substring.
→ `200` paginated envelope of `Employee`.

### `GET /employees/{id}`
→ `200` `Employee` · `404` `employee_not_found`.

### `POST /employees`
Body: `first_name`, `last_name`, `email`, `gender`, `hire_date`, `department_id`,
`job_role_id`, `level_id`, `country_id`, `manager_id?`, `employment_status?`,
and optional `initial_salary: { "amount": "...", "currency": "INR" }`.
→ `201` `Employee` · `409` `email_already_exists` · `422` validation.

### `PATCH /employees/{id}`
Body: any subset of the non-salary fields above. **Salary cannot be changed here.**
→ `200` `Employee` · `404` · `422`.

### `GET /employees/{id}/salary-history`
→ `200` `{ "items": [ SalaryRecord, ... ] }`, newest first.

### `POST /employees/{id}/salary`
Body:
```json
{ "amount": "2650000.00", "currency": "INR", "effective_from": "2025-04-01",
  "change_reason": "annual_review", "note": "optional" }
```
Closes the open record (`effective_to = effective_from - 1 day`) and inserts the new one, in one
transaction.
→ `201` `SalaryRecord` · `404` · `422` `salary_effective_date_invalid` (date not after the
current record's `effective_from`) · `422` validation.

### `GET /employees/export` — CSV
Accepts the same filters as `GET /employees`. → `200` `text/csv`, `Content-Disposition: attachment`.

### `POST /employees/import` — `multipart/form-data`, field `file` (CSV)
→ `200`
```json
{ "total_rows": 120, "created": 100, "updated": 15, "failed": 5,
  "errors": [ { "row": 12, "field": "email", "message": "Invalid email" } ] }
```
Valid rows are applied; invalid rows are reported and skipped.

### `GET /reference`
All lookup data for filter dropdowns in one call.
→ `200`
```json
{ "departments": [RefItem], "job_roles": [RefItem], "levels": [RefItem],
  "countries": [RefItem], "genders": ["female", ...],
  "employment_statuses": ["active", ...], "change_reasons": ["initial", ...],
  "base_currency": "USD" }
```

---

## Analytics — all amounts in `base_currency`, all accept the same filter params as `GET /employees`

### `GET /analytics/summary`
```json
{ "base_currency": "USD", "headcount": 10000, "active_headcount": 9400,
  "total_annual_payroll": "612450000.00", "mean_salary": "65154.25",
  "median_salary": "58900.00", "min_salary": "12000.00", "max_salary": "410000.00",
  "countries": 8, "departments": 9,
  "band_coverage_pct": 96.4 }
```

### `GET /analytics/distribution`
```json
{ "base_currency": "USD",
  "percentiles": { "p10": "...", "p25": "...", "p50": "...", "p75": "...", "p90": "..." },
  "histogram": [ { "lower": "0.00", "upper": "20000.00", "count": 812 }, ... ] }
```
Bucket count defaults to 12; query param `buckets` (5–30).

### `GET /analytics/by-dimension?dimension=department|country|job_role|level`
```json
{ "base_currency": "USD", "dimension": "department",
  "groups": [ { "id": 3, "name": "Engineering", "headcount": 2400,
                "median": "72000.00", "mean": "75300.00",
                "p25": "58000.00", "p75": "92000.00",
                "min": "31000.00", "max": "310000.00",
                "total_payroll": "180720000.00" } ] }
```
Sorted by headcount desc.

### `GET /analytics/pay-equity?dimension=gender&group_by=job_role_level`
```json
{ "base_currency": "USD", "min_sample_size": 5,
  "overall": { "reference": "male", "comparison": "female",
               "reference_median": "64000.00", "comparison_median": "60800.00",
               "gap_pct": 5.0, "sample_reference": 5200, "sample_comparison": 4100 },
  "groups": [ { "key": "Software Engineer · L3", "job_role": "Software Engineer",
                "level": "L3", "reference_median": "70000.00",
                "comparison_median": "68600.00", "gap_pct": 2.0,
                "sample_reference": 210, "sample_comparison": 180,
                "sufficient_sample": true } ],
  "suppressed_groups": 14 }
```
`gap_pct` = `(reference_median - comparison_median) / reference_median * 100`, positive meaning
the comparison group is paid less. Groups below `min_sample_size` on either side are excluded
from `groups` and counted in `suppressed_groups`.

### `GET /analytics/band-health`
```json
{ "base_currency": "USD",
  "below": 412, "within": 8900, "above": 588, "unbanded": 100,
  "below_pct": 4.1, "within_pct": 89.0, "above_pct": 5.9,
  "outliers": [ { "employee_id": 55, "full_name": "...", "department": "Engineering",
                  "job_role": "Software Engineer", "level": "L4", "country": "US",
                  "salary_base": "48000.00", "band_min": "80000.00", "band_max": "120000.00",
                  "compa_ratio": 0.48, "position": "below", "deviation_pct": -40.0 } ] }
```
`outliers` = 20 largest absolute deviations from the nearest band edge, worst first.

---

## Health
`GET /health` → `{ "status": "ok", "database": "ok", "employee_count": 10000 }`
