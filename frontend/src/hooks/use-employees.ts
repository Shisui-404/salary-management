"use client";

import { useQuery } from "@tanstack/react-query";
import { getEmployee, listEmployees } from "@/lib/api/employees";
import { getSalaryHistory } from "@/lib/api/employees";
import type { EmployeeListParams } from "@/lib/api/types";

export function useEmployeeList(params: EmployeeListParams) {
  return useQuery({
    queryKey: ["employees", params],
    queryFn: () => listEmployees(params),
    placeholderData: (previous) => previous,
  });
}

export function useEmployee(id: number) {
  return useQuery({
    queryKey: ["employee", id],
    queryFn: () => getEmployee(id),
    enabled: Number.isFinite(id),
  });
}

export function useSalaryHistory(employeeId: number) {
  return useQuery({
    queryKey: ["salary-history", employeeId],
    queryFn: () => getSalaryHistory(employeeId),
    enabled: Number.isFinite(employeeId),
  });
}
