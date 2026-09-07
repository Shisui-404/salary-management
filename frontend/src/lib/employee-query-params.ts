import type {
  BandPosition,
  EmployeeListParams,
  EmploymentStatus,
  Gender,
  SortField,
} from "@/lib/api/types";

/**
 * UI-shaped filter/sort/page state for the employee directory, and its
 * round-trip to/from URL query params so views are shareable and
 * back/forward-navigable (per the requirements brief).
 *
 * Kept deliberately separate from `EmployeeListParams` (the wire shape):
 * this uses a 1-based `page` + `pageSize` instead of `limit`/`offset`, and a
 * split `sort`/`sortDir` instead of the API's `-field` prefix convention,
 * because that's the shape components/URLs want to work with.
 */
export interface DirectoryFilters {
  search: string;
  departmentId?: number;
  countryId?: number;
  jobRoleId?: number;
  levelId?: number;
  employmentStatus?: EmploymentStatus;
  gender?: Gender;
  bandPosition?: BandPosition;
  minSalaryBase?: number;
  maxSalaryBase?: number;
  sort: SortField;
  sortDir: "asc" | "desc";
  page: number;
  pageSize: number;
}

export const DEFAULT_PAGE_SIZE = 25;

export const DEFAULT_DIRECTORY_FILTERS: DirectoryFilters = {
  search: "",
  sort: "name",
  sortDir: "asc",
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
};

const SORT_FIELDS: SortField[] = [
  "name",
  "salary",
  "hire_date",
  "compa_ratio",
  "department",
];
const EMPLOYMENT_STATUSES: EmploymentStatus[] = [
  "active",
  "on_leave",
  "terminated",
];
const GENDERS: Gender[] = ["female", "male", "non_binary", "undisclosed"];
const BAND_POSITIONS: BandPosition[] = [
  "below",
  "within",
  "above",
  "unbanded",
];

function parseIntParam(
  params: URLSearchParams,
  key: string,
): number | undefined {
  const raw = params.get(key);
  if (raw === null || raw === "") return undefined;
  const n = Number(raw);
  return Number.isFinite(n) ? n : undefined;
}

function parseEnumParam<T extends string>(
  params: URLSearchParams,
  key: string,
  allowed: readonly T[],
): T | undefined {
  const raw = params.get(key);
  if (raw === null) return undefined;
  return (allowed as readonly string[]).includes(raw) ? (raw as T) : undefined;
}

/** Parses a `URLSearchParams` into directory filter state, filling in defaults. */
export function searchParamsToFilters(
  params: URLSearchParams,
): DirectoryFilters {
  const page = parseIntParam(params, "page");
  const pageSize = parseIntParam(params, "pageSize");
  return {
    search: params.get("q") ?? "",
    departmentId: parseIntParam(params, "department"),
    countryId: parseIntParam(params, "country"),
    jobRoleId: parseIntParam(params, "role"),
    levelId: parseIntParam(params, "level"),
    employmentStatus: parseEnumParam(
      params,
      "status",
      EMPLOYMENT_STATUSES,
    ),
    gender: parseEnumParam(params, "gender", GENDERS),
    bandPosition: parseEnumParam(params, "band", BAND_POSITIONS),
    minSalaryBase: parseIntParam(params, "minSalary"),
    maxSalaryBase: parseIntParam(params, "maxSalary"),
    sort: parseEnumParam(params, "sort", SORT_FIELDS) ?? "name",
    sortDir: params.get("dir") === "desc" ? "desc" : "asc",
    page: page && page > 0 ? page : 1,
    pageSize: pageSize && pageSize > 0 ? Math.min(pageSize, 100) : DEFAULT_PAGE_SIZE,
  };
}

/**
 * Serialises directory filter state to `URLSearchParams`, omitting any key
 * that's at its default value — keeps shared URLs short and readable.
 */
export function filtersToSearchParams(
  filters: DirectoryFilters,
): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.search) params.set("q", filters.search);
  if (filters.departmentId !== undefined)
    params.set("department", String(filters.departmentId));
  if (filters.countryId !== undefined)
    params.set("country", String(filters.countryId));
  if (filters.jobRoleId !== undefined)
    params.set("role", String(filters.jobRoleId));
  if (filters.levelId !== undefined)
    params.set("level", String(filters.levelId));
  if (filters.employmentStatus) params.set("status", filters.employmentStatus);
  if (filters.gender) params.set("gender", filters.gender);
  if (filters.bandPosition) params.set("band", filters.bandPosition);
  if (filters.minSalaryBase !== undefined)
    params.set("minSalary", String(filters.minSalaryBase));
  if (filters.maxSalaryBase !== undefined)
    params.set("maxSalary", String(filters.maxSalaryBase));
  if (filters.sort !== "name") params.set("sort", filters.sort);
  if (filters.sortDir !== "asc") params.set("dir", filters.sortDir);
  if (filters.page !== 1) params.set("page", String(filters.page));
  if (filters.pageSize !== DEFAULT_PAGE_SIZE)
    params.set("pageSize", String(filters.pageSize));
  return params;
}

/** Converts UI filter state into the API's `EmployeeListParams` wire shape. */
export function filtersToApiParams(
  filters: DirectoryFilters,
): EmployeeListParams {
  return {
    search: filters.search || undefined,
    department_id: filters.departmentId,
    country_id: filters.countryId,
    job_role_id: filters.jobRoleId,
    level_id: filters.levelId,
    employment_status: filters.employmentStatus,
    gender: filters.gender,
    band_position: filters.bandPosition,
    min_salary_base: filters.minSalaryBase,
    max_salary_base: filters.maxSalaryBase,
    sort: `${filters.sortDir === "desc" ? "-" : ""}${filters.sort}`,
    limit: filters.pageSize,
    offset: (filters.page - 1) * filters.pageSize,
  };
}
