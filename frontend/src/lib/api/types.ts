/**
 * Types mirroring `docs/api-contract.md` exactly.
 *
 * Money is always a decimal string over the wire (never a JSON number) — see the
 * "Conventions" section of the contract. Never `parseFloat` these for arithmetic;
 * only for display formatting (see `src/lib/format.ts`).
 */

export type Gender = "female" | "male" | "non_binary" | "undisclosed";
export type EmploymentStatus = "active" | "on_leave" | "terminated";
export type BandPosition = "below" | "within" | "above" | "unbanded";
export type ChangeReason =
  | "initial"
  | "annual_review"
  | "promotion"
  | "market_adjustment"
  | "role_change"
  | "correction";

export type SortField = "name" | "salary" | "hire_date" | "compa_ratio" | "department";
export type Dimension = "department" | "country" | "job_role" | "level";

/** Generic paginated envelope: `{ items, total, limit, offset }`. */
export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Money {
  amount: string;
  currency: string;
}

export interface RefItem {
  id: number;
  name: string;
}

export interface LevelRef extends RefItem {
  rank: number;
}

export interface CountryRef extends RefItem {
  code: string;
  currency: string;
}

export interface CurrentSalary {
  amount: string;
  currency: string;
  amount_base: string;
  base_currency: string;
  effective_from: string;
  change_reason: ChangeReason;
}

export interface Band {
  min: string;
  mid: string;
  max: string;
  currency: string;
}

export interface Employee {
  id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  gender: Gender;
  hire_date: string;
  employment_status: EmploymentStatus;
  department: RefItem;
  job_role: RefItem;
  level: LevelRef;
  country: CountryRef;
  manager_id: number | null;
  current_salary: CurrentSalary | null;
  compa_ratio: number | null;
  band_position: BandPosition;
  band: Band | null;
}

export interface SalaryRecord {
  id: number;
  employee_id: number;
  amount: string;
  currency: string;
  amount_base: string;
  base_currency: string;
  effective_from: string;
  effective_to: string | null;
  change_reason: ChangeReason;
  note: string | null;
  created_at: string;
  change_pct: number | null;
}

export interface ReferenceData {
  departments: RefItem[];
  job_roles: RefItem[];
  levels: LevelRef[];
  countries: CountryRef[];
  genders: Gender[];
  employment_statuses: EmploymentStatus[];
  change_reasons: ChangeReason[];
  base_currency: string;
}

/**
 * Query params shared by `GET /employees` and every `/analytics/*` endpoint.
 *
 * Declared as a `type` (not `interface`) so it gets TypeScript's implicit
 * index signature for object type literals — needed to pass it straight as
 * the `query` object to `fetchJson` (typed `Record<string, ...>`).
 */
export type EmployeeFilters = {
  search?: string;
  department_id?: number;
  country_id?: number;
  job_role_id?: number;
  level_id?: number;
  employment_status?: EmploymentStatus;
  gender?: Gender;
  band_position?: BandPosition;
  min_salary_base?: number;
  max_salary_base?: number;
};

export type EmployeeListParams = EmployeeFilters & {
  sort?: `${"" | "-"}${SortField}`;
  limit?: number;
  offset?: number;
};

export interface CreateEmployeeInput {
  first_name: string;
  last_name: string;
  email: string;
  gender: Gender;
  hire_date: string;
  department_id: number;
  job_role_id: number;
  level_id: number;
  country_id: number;
  manager_id?: number;
  employment_status?: EmploymentStatus;
  initial_salary?: Money;
}

export interface RecordSalaryInput {
  amount: string;
  currency: string;
  effective_from: string;
  change_reason: ChangeReason;
  note?: string;
}

export interface ImportError {
  row: number;
  field: string;
  message: string;
}

export interface ImportReport {
  total_rows: number;
  created: number;
  updated: number;
  failed: number;
  errors: ImportError[];
}

/** `{ error: { code, message, details } }` — every 4xx/5xx response. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: { field: string; message: string }[] | null;
  };
}

// ---- Analytics ----

export interface AnalyticsSummary {
  base_currency: string;
  headcount: number;
  active_headcount: number;
  total_annual_payroll: string;
  mean_salary: string;
  median_salary: string;
  min_salary: string;
  max_salary: string;
  countries: number;
  departments: number;
  band_coverage_pct: number;
}

export interface DistributionBucket {
  lower: string;
  upper: string;
  count: number;
}

export interface AnalyticsDistribution {
  base_currency: string;
  percentiles: {
    p10: string;
    p25: string;
    p50: string;
    p75: string;
    p90: string;
  };
  histogram: DistributionBucket[];
}

export interface DimensionGroup {
  id: number;
  name: string;
  headcount: number;
  median: string;
  mean: string;
  p25: string;
  p75: string;
  min: string;
  max: string;
  total_payroll: string;
}

export interface AnalyticsByDimension {
  base_currency: string;
  dimension: Dimension;
  groups: DimensionGroup[];
}

export interface PayEquityOverall {
  reference: string;
  comparison: string;
  reference_median: string;
  comparison_median: string;
  gap_pct: number;
  sample_reference: number;
  sample_comparison: number;
}

export interface PayEquityGroup {
  key: string;
  job_role: string;
  level: string;
  reference_median: string;
  comparison_median: string;
  gap_pct: number;
  sample_reference: number;
  sample_comparison: number;
  sufficient_sample: boolean;
}

export interface AnalyticsPayEquity {
  base_currency: string;
  min_sample_size: number;
  /**
   * `null` when one side of the comparison has no employees at all — e.g. the
   * view is filtered to a single gender. The backend declares this nullable
   * (`app/schemas/analytics.py`), so every use site must guard it.
   */
  overall: PayEquityOverall | null;
  groups: PayEquityGroup[];
  suppressed_groups: number;
}

export interface BandHealthOutlier {
  employee_id: number;
  full_name: string;
  department: string;
  job_role: string;
  level: string;
  country: string;
  salary_base: string;
  band_min: string;
  band_max: string;
  compa_ratio: number;
  position: BandPosition;
  deviation_pct: number;
}

export interface AnalyticsBandHealth {
  base_currency: string;
  below: number;
  within: number;
  above: number;
  unbanded: number;
  below_pct: number;
  within_pct: number;
  above_pct: number;
  outliers: BandHealthOutlier[];
}

export interface HealthCheck {
  status: string;
  database: string;
  employee_count: number;
}
