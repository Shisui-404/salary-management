import { describe, expect, it } from "vitest";
import {
  DEFAULT_DIRECTORY_FILTERS,
  type DirectoryFilters,
  filtersToApiParams,
  filtersToSearchParams,
  searchParamsToFilters,
} from "./employee-query-params";

describe("employee directory filter <-> URL round trip", () => {
  it("parsing an empty URL yields the defaults", () => {
    expect(searchParamsToFilters(new URLSearchParams())).toEqual(
      DEFAULT_DIRECTORY_FILTERS,
    );
  });

  it("serialising the defaults produces an empty query string", () => {
    // Keeps shared URLs clean: /employees with no params, not
    // /employees?q=&sort=name&dir=asc&page=1&pageSize=25.
    expect(filtersToSearchParams(DEFAULT_DIRECTORY_FILTERS).toString()).toBe("");
  });

  it("round-trips a fully populated filter state: filters -> URL -> filters", () => {
    const filters: DirectoryFilters = {
      search: "ada lovelace",
      departmentId: 3,
      countryId: 1,
      jobRoleId: 5,
      levelId: 2,
      employmentStatus: "on_leave",
      gender: "female",
      bandPosition: "below",
      minSalaryBase: 40000,
      maxSalaryBase: 120000,
      sort: "compa_ratio",
      sortDir: "desc",
      page: 3,
      pageSize: 50,
    };

    const params = filtersToSearchParams(filters);
    expect(searchParamsToFilters(params)).toEqual(filters);
  });

  it("round-trips a URL -> filters -> URL for an arbitrary param order", () => {
    const raw = "page=2&sort=hire_date&dir=desc&department=3&q=grace";
    const params = new URLSearchParams(raw);
    const filters = searchParamsToFilters(params);
    const roundTripped = filtersToSearchParams(filters);

    // Compare as sets of key/value pairs — param order isn't semantic, so
    // sort both sides' entries before comparing.
    const sortedEntries = (params: URLSearchParams) =>
      [...params.entries()].sort(([a], [b]) => a.localeCompare(b));
    expect(sortedEntries(roundTripped)).toEqual(
      sortedEntries(new URLSearchParams(raw)),
    );
  });

  it("ignores unknown or malformed values instead of throwing", () => {
    const params = new URLSearchParams(
      "department=not-a-number&status=on_the_moon&page=-5&pageSize=0",
    );
    const filters = searchParamsToFilters(params);
    expect(filters.departmentId).toBeUndefined();
    expect(filters.employmentStatus).toBeUndefined();
    expect(filters.page).toBe(1);
    expect(filters.pageSize).toBe(25);
  });

  it("clamps pageSize to the contract's max of 100", () => {
    const filters = searchParamsToFilters(new URLSearchParams("pageSize=500"));
    expect(filters.pageSize).toBe(100);
  });

  it("omits default values from the serialised URL", () => {
    const params = filtersToSearchParams({
      ...DEFAULT_DIRECTORY_FILTERS,
      search: "priya",
    });
    expect(params.get("q")).toBe("priya");
    expect(params.has("sort")).toBe(false);
    expect(params.has("page")).toBe(false);
  });
});

describe("filtersToApiParams", () => {
  it("converts 1-based page/pageSize into limit/offset", () => {
    const api = filtersToApiParams({
      ...DEFAULT_DIRECTORY_FILTERS,
      page: 3,
      pageSize: 25,
    });
    expect(api.limit).toBe(25);
    expect(api.offset).toBe(50);
  });

  it("encodes descending sort with the API's `-field` prefix convention", () => {
    const api = filtersToApiParams({
      ...DEFAULT_DIRECTORY_FILTERS,
      sort: "salary",
      sortDir: "desc",
    });
    expect(api.sort).toBe("-salary");
  });

  it("encodes ascending sort with no prefix", () => {
    const api = filtersToApiParams({
      ...DEFAULT_DIRECTORY_FILTERS,
      sort: "salary",
      sortDir: "asc",
    });
    expect(api.sort).toBe("salary");
  });

  it("drops an empty search string rather than sending an empty param", () => {
    const api = filtersToApiParams(DEFAULT_DIRECTORY_FILTERS);
    expect(api.search).toBeUndefined();
  });
});
