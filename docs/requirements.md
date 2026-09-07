# Requirements — ACME Salary Management

_One-page requirements document, written before implementation._

## 1. Goal

Give ACME's HR Manager a single web application to **manage** salary data for ~10,000 employees
across multiple countries, replacing the current spreadsheet process, and to **answer questions
about how the organisation pays people** without exporting anything to Excel.

The second half of that sentence is the real product. Spreadsheets already store salaries
adequately; what they do badly is answer "are we paying this person fairly?", "where are we out
of band?", and "what is our gender pay gap in Engineering L4?" — reliably, across currencies,
on demand. The application is designed around those questions.

## 2. User persona

**Priya, HR Manager at ACME.** Not a data analyst. Owns compensation data quality, runs the
annual review cycle, fields "am I paid fairly?" escalations from managers, and reports pay
equity to leadership. Needs answers in seconds and needs to trust them.

### Jobs to be done
| # | Job | Why it matters |
|---|---|---|
| J1 | Find any employee and see their full compensation picture | Daily lookup; escalations |
| J2 | Record a raise/adjustment without destroying salary history | Audit + review-cycle traceability |
| J3 | See where an employee sits against their salary band | Fairness decisions, offer approvals |
| J4 | Compare pay across departments, countries, roles and levels | Budgeting, benchmarking |
| J5 | Detect pay-equity gaps and out-of-band outliers | Legal/ethical risk, leadership reporting |
| J6 | Bulk-load and export data | Migration off Excel; sharing with finance |

## 3. Scope — what we are building

**Employee & salary management**
- Employee directory over 10,000 records: server-side pagination, full-text-ish search,
  faceted filters (department, country, job role, level, employment status, salary range),
  multi-column sort.
- Employee profile: personal/job attributes, current compensation, salary band position.
- Create and update employees; deactivate (soft state) rather than delete.
- **Effective-dated salary revisions**: recording a raise closes the current salary record and
  opens a new one. Salary is an append-only timeline, never an overwritten field.
- Full salary history per employee with change reason and effective dates.

**Compensation intelligence** (the differentiator)
- Multi-currency: every salary is stored in its local currency and normalised to a configurable
  base currency (USD) for any cross-country comparison.
- Salary bands per (job role, level, country) with min/mid/max, yielding **compa-ratio** and a
  below/within/above classification per employee.
- Org dashboard: headcount, annualised payroll cost, median/mean, salary distribution
  histogram, percentiles (p10/p25/p50/p75/p90).
- Breakdown by dimension: median, spread and headcount per department / country / role / level.
- **Pay-equity view**: median pay gap by gender within comparable (role, level) groups, with a
  minimum-sample-size guard so small groups do not produce misleading percentages.
- **Band health**: share of employees below / within / above band, plus a ranked outlier list.

**Data movement**
- CSV export of the current filtered view.
- CSV import with per-row validation and an error report (no partial silent failures).

**Engineering**
- Seed script generating a deterministic, realistic 10,000-employee organisation.
- Meaningful unit tests over the compensation domain logic; API contract tests.
- Docker Compose for a one-command run.

## 4. Out of scope — and why

| Excluded | Reasoning |
|---|---|
| Authentication, authorisation, RBAC | Single known persona (HR Manager). Auth is well-understood, adds no signal about compensation-domain judgement, and would consume budget better spent on the analytics that make this product useful. Called out as the **first thing to add** before any real deployment. |
| Payroll execution, payslips, tax & statutory deductions | A different bounded context with its own compliance surface per country. The brief is managing *salary data* and reasoning about it, not disbursing money. |
| Bonus, equity, benefits, total-rewards modelling | Would multiply the data model and dilute the core. Base salary is the dimension the HR manager compares on first; the schema leaves room to add components later. |
| Live FX rate feed | Rates are a seeded, dated table. A live feed adds a network dependency and non-deterministic tests for no gain in demonstrating the design — the conversion boundary is isolated so swapping in a provider is a one-file change. |
| Approval workflows for raises | Requires roles and org hierarchy, which requires auth. Deferred with auth. |
| Performance reviews / ratings | Adjacent product. Salary history carries a `change_reason` which is enough to explain a raise. |
| Internationalisation of the UI | English-only; the *data* is multi-country, which is the part that matters here. |
| Real-time collaboration, notifications, email | No evidence of the need in the brief. |

## 5. Non-functional requirements

- **Correctness of money.** No floating-point arithmetic on currency anywhere. Amounts are
  stored as integer minor units with an ISO-4217 code and travel over the API as decimal
  strings.
- **Scale.** Every list and aggregate must stay responsive at 10,000 employees / ~25,000 salary
  records. No endpoint may load the full table into memory; aggregation happens in SQL.
- **Determinism.** Seeded data and tests are reproducible run-to-run; tests do no network I/O
  and take seconds, not minutes.
- **Maintainability.** Clear layering (API → service → repository → model); domain rules live in
  services and are unit-testable without a database.

## 6. Success criteria

1. Priya can find any of 10,000 employees in under a second and see their band position.
2. Recording a raise preserves the prior salary and its effective dates.
3. The dashboard answers "how do we pay people?" across currencies without an export.
4. Pay-equity and band-health views surface a real, actionable list — not just a number.
5. A clean checkout runs the full stack with one command and a green test suite.
