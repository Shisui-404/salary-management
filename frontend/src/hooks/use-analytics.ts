"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getBandHealth,
  getByDimension,
  getDistribution,
  getPayEquity,
  getSummary,
} from "@/lib/api/analytics";
import type { Dimension, EmployeeFilters } from "@/lib/api/types";

export function useAnalyticsSummary(filters: EmployeeFilters = {}) {
  return useQuery({
    queryKey: ["analytics", "summary", filters],
    queryFn: () => getSummary(filters),
  });
}

export function useAnalyticsDistribution(
  filters: EmployeeFilters & { buckets?: number } = {},
) {
  return useQuery({
    queryKey: ["analytics", "distribution", filters],
    queryFn: () => getDistribution(filters),
  });
}

export function useAnalyticsByDimension(
  dimension: Dimension,
  filters: EmployeeFilters = {},
) {
  return useQuery({
    queryKey: ["analytics", "by-dimension", dimension, filters],
    queryFn: () => getByDimension(dimension, filters),
  });
}

export function useAnalyticsPayEquity(filters: EmployeeFilters = {}) {
  return useQuery({
    queryKey: ["analytics", "pay-equity", filters],
    queryFn: () => getPayEquity(filters),
  });
}

export function useAnalyticsBandHealth(filters: EmployeeFilters = {}) {
  return useQuery({
    queryKey: ["analytics", "band-health", filters],
    queryFn: () => getBandHealth(filters),
  });
}
