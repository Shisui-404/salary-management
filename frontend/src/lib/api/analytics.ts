import { fetchJson } from "./client";
import type {
  AnalyticsBandHealth,
  AnalyticsByDimension,
  AnalyticsDistribution,
  AnalyticsPayEquity,
  AnalyticsSummary,
  Dimension,
  EmployeeFilters,
} from "./types";

export function getSummary(
  filters: EmployeeFilters = {},
): Promise<AnalyticsSummary> {
  return fetchJson<AnalyticsSummary>("/analytics/summary", { query: filters });
}

export function getDistribution(
  filters: EmployeeFilters & { buckets?: number } = {},
): Promise<AnalyticsDistribution> {
  return fetchJson<AnalyticsDistribution>("/analytics/distribution", {
    query: filters,
  });
}

export function getByDimension(
  dimension: Dimension,
  filters: EmployeeFilters = {},
): Promise<AnalyticsByDimension> {
  return fetchJson<AnalyticsByDimension>("/analytics/by-dimension", {
    query: { ...filters, dimension },
  });
}

export function getPayEquity(
  filters: EmployeeFilters & { dimension?: string; group_by?: string } = {},
): Promise<AnalyticsPayEquity> {
  return fetchJson<AnalyticsPayEquity>("/analytics/pay-equity", {
    query: { dimension: "gender", group_by: "job_role_level", ...filters },
  });
}

export function getBandHealth(
  filters: EmployeeFilters = {},
): Promise<AnalyticsBandHealth> {
  return fetchJson<AnalyticsBandHealth>("/analytics/band-health", {
    query: filters,
  });
}
