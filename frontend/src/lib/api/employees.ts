import { fetchBlob, fetchJson } from "./client";
import type {
  CreateEmployeeInput,
  Employee,
  EmployeeListParams,
  ImportReport,
  Paginated,
  RecordSalaryInput,
  SalaryRecord,
} from "./types";

export function listEmployees(
  params: EmployeeListParams,
): Promise<Paginated<Employee>> {
  return fetchJson<Paginated<Employee>>("/employees", { query: params });
}

export function getEmployee(id: number): Promise<Employee> {
  return fetchJson<Employee>(`/employees/${id}`);
}

export function createEmployee(input: CreateEmployeeInput): Promise<Employee> {
  return fetchJson<Employee>("/employees", { method: "POST", body: input });
}

export function getSalaryHistory(
  employeeId: number,
): Promise<{ items: SalaryRecord[] }> {
  return fetchJson<{ items: SalaryRecord[] }>(
    `/employees/${employeeId}/salary-history`,
  );
}

export function recordSalary(
  employeeId: number,
  input: RecordSalaryInput,
): Promise<SalaryRecord> {
  return fetchJson<SalaryRecord>(`/employees/${employeeId}/salary`, {
    method: "POST",
    body: input,
  });
}

export async function exportEmployeesCsv(
  filters: EmployeeListParams,
): Promise<Blob> {
  return fetchBlob("/employees/export", filters);
}

export function importEmployeesCsv(file: File): Promise<ImportReport> {
  const form = new FormData();
  form.append("file", file);
  return fetchJson<ImportReport>("/employees/import", {
    method: "POST",
    body: form,
  });
}
