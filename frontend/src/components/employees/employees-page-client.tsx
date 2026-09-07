"use client";

import { useMemo } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { useDirectoryFilters } from "@/hooks/use-directory-filters";
import { useEmployeeList } from "@/hooks/use-employees";
import { useReference } from "@/hooks/use-reference";
import { filtersToApiParams } from "@/lib/employee-query-params";
import type { SortField } from "@/lib/api/types";
import { EmployeeFilters } from "./employee-filters";
import { EmployeesTable } from "./employees-table";
import { PaginationControls } from "./pagination-controls";
import { ExportButton } from "./export-button";
import { AddEmployeeDialog } from "./add-employee-dialog";

export function EmployeesPageClient() {
  const { filters, setFilters, resetFilters } = useDirectoryFilters();
  const referenceQuery = useReference();
  const apiParams = useMemo(() => filtersToApiParams(filters), [filters]);
  const employeesQuery = useEmployeeList(apiParams);

  const activeFilterCount = [
    filters.search,
    filters.departmentId,
    filters.countryId,
    filters.jobRoleId,
    filters.levelId,
    filters.employmentStatus,
    filters.gender,
    filters.bandPosition,
    filters.minSalaryBase,
    filters.maxSalaryBase,
  ].filter((value) => value !== undefined && value !== "").length;

  function handleSortChange(field: SortField) {
    if (filters.sort === field) {
      setFilters({ sort: field, sortDir: filters.sortDir === "asc" ? "desc" : "asc" });
    } else {
      setFilters({ sort: field, sortDir: "asc" });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Employees"
        description="Search, filter and manage ACME's global workforce."
        actions={
          <>
            <ExportButton filters={apiParams} />
            <AddEmployeeDialog reference={referenceQuery.data} />
          </>
        }
      />

      <EmployeeFilters
        filters={filters}
        reference={referenceQuery.data}
        onFilterChange={setFilters}
        onReset={resetFilters}
        activeFilterCount={activeFilterCount}
      />

      {employeesQuery.isError ? (
        <ErrorState
          error={employeesQuery.error}
          onRetry={() => employeesQuery.refetch()}
          title="Couldn't load employees"
        />
      ) : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <EmployeesTable
            data={employeesQuery.data?.items ?? []}
            isLoading={employeesQuery.isLoading}
            sort={filters.sort}
            sortDir={filters.sortDir}
            onSortChange={handleSortChange}
          />
          {employeesQuery.data && (
            <PaginationControls
              page={filters.page}
              pageSize={filters.pageSize}
              total={employeesQuery.data.total}
              onPageChange={(page) => setFilters({ page })}
            />
          )}
        </div>
      )}
    </div>
  );
}
