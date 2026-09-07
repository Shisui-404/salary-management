"use client";

import { useEffect } from "react";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { DirectoryFilters } from "@/lib/employee-query-params";
import type { ReferenceData } from "@/lib/api/types";
import { humanizeEnum } from "@/lib/format";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useSyncedState } from "@/hooks/use-synced-state";

const ALL = "all";

interface EmployeeFiltersProps {
  filters: DirectoryFilters;
  reference?: ReferenceData;
  onFilterChange: (patch: Partial<DirectoryFilters>) => void;
  onReset: () => void;
  activeFilterCount: number;
}

export function EmployeeFilters({
  filters,
  reference,
  onFilterChange,
  onReset,
  activeFilterCount,
}: EmployeeFiltersProps) {
  // Local "draft" copies of URL-derived filter state, debounced before
  // being pushed back out. `useSyncedState` (rather than a
  // useState+useEffect mirror) keeps these in sync when the filter changes
  // externally — browser back/forward, or the "Clear filters" action —
  // without an extra render-commit cycle.
  const [search, setSearch] = useSyncedState(filters.search);
  const debouncedSearch = useDebouncedValue(search, 300);
  const [minSalary, setMinSalary] = useSyncedState(
    filters.minSalaryBase?.toString() ?? "",
  );
  const [maxSalary, setMaxSalary] = useSyncedState(
    filters.maxSalaryBase?.toString() ?? "",
  );
  const debouncedMin = useDebouncedValue(minSalary, 300);
  const debouncedMax = useDebouncedValue(maxSalary, 300);

  useEffect(() => {
    if (debouncedSearch !== filters.search) {
      onFilterChange({ search: debouncedSearch });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  useEffect(() => {
    const parsed = debouncedMin === "" ? undefined : Number(debouncedMin);
    if (parsed !== filters.minSalaryBase) {
      onFilterChange({ minSalaryBase: parsed });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedMin]);

  useEffect(() => {
    const parsed = debouncedMax === "" ? undefined : Number(debouncedMax);
    if (parsed !== filters.maxSalaryBase) {
      onFilterChange({ maxSalaryBase: parsed });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedMax]);

  return (
    <div className="space-y-4 rounded-lg border bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Label htmlFor="employee-search" className="sr-only">
            Search employees
          </Label>
          <Input
            id="employee-search"
            placeholder="Search by name, email or employee code…"
            className="pl-8"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        {activeFilterCount > 0 && (
          <Button variant="ghost" size="sm" onClick={onReset} className="gap-1.5">
            <X className="size-3.5" aria-hidden="true" />
            Clear {activeFilterCount} filter{activeFilterCount === 1 ? "" : "s"}
          </Button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <FilterField label="Department" id="filter-department">
          <Select
            value={filters.departmentId?.toString() ?? ALL}
            onValueChange={(value) =>
              onFilterChange({
                departmentId: value === ALL ? undefined : Number(value),
              })
            }
          >
            <SelectTrigger id="filter-department" className="w-full">
              <SelectValue placeholder="All departments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All departments</SelectItem>
              {reference?.departments.map((dept) => (
                <SelectItem key={dept.id} value={dept.id.toString()}>
                  {dept.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FilterField>

        <FilterField label="Country" id="filter-country">
          <Select
            value={filters.countryId?.toString() ?? ALL}
            onValueChange={(value) =>
              onFilterChange({
                countryId: value === ALL ? undefined : Number(value),
              })
            }
          >
            <SelectTrigger id="filter-country" className="w-full">
              <SelectValue placeholder="All countries" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All countries</SelectItem>
              {reference?.countries.map((country) => (
                <SelectItem key={country.id} value={country.id.toString()}>
                  {country.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FilterField>

        <FilterField label="Job role" id="filter-job-role">
          <Select
            value={filters.jobRoleId?.toString() ?? ALL}
            onValueChange={(value) =>
              onFilterChange({
                jobRoleId: value === ALL ? undefined : Number(value),
              })
            }
          >
            <SelectTrigger id="filter-job-role" className="w-full">
              <SelectValue placeholder="All roles" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All roles</SelectItem>
              {reference?.job_roles.map((role) => (
                <SelectItem key={role.id} value={role.id.toString()}>
                  {role.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FilterField>

        <FilterField label="Level" id="filter-level">
          <Select
            value={filters.levelId?.toString() ?? ALL}
            onValueChange={(value) =>
              onFilterChange({
                levelId: value === ALL ? undefined : Number(value),
              })
            }
          >
            <SelectTrigger id="filter-level" className="w-full">
              <SelectValue placeholder="All levels" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All levels</SelectItem>
              {reference?.levels.map((level) => (
                <SelectItem key={level.id} value={level.id.toString()}>
                  {level.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FilterField>

        <FilterField label="Status" id="filter-status">
          <Select
            value={filters.employmentStatus ?? ALL}
            onValueChange={(value) =>
              onFilterChange({
                employmentStatus:
                  value === ALL
                    ? undefined
                    : (value as DirectoryFilters["employmentStatus"]),
              })
            }
          >
            <SelectTrigger id="filter-status" className="w-full">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All statuses</SelectItem>
              {reference?.employment_statuses.map((status) => (
                <SelectItem key={status} value={status}>
                  {humanizeEnum(status)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FilterField>

        <FilterField label="Band position" id="filter-band-position">
          <Select
            value={filters.bandPosition ?? ALL}
            onValueChange={(value) =>
              onFilterChange({
                bandPosition:
                  value === ALL
                    ? undefined
                    : (value as DirectoryFilters["bandPosition"]),
              })
            }
          >
            <SelectTrigger id="filter-band-position" className="w-full">
              <SelectValue placeholder="Any position" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Any position</SelectItem>
              <SelectItem value="below">Below band</SelectItem>
              <SelectItem value="within">Within band</SelectItem>
              <SelectItem value="above">Above band</SelectItem>
              <SelectItem value="unbanded">Unbanded</SelectItem>
            </SelectContent>
          </Select>
        </FilterField>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:max-w-xs">
        <FilterField
          label={`Min salary (${reference?.base_currency ?? "USD"})`}
          id="filter-min-salary"
        >
          <Input
            id="filter-min-salary"
            type="number"
            inputMode="numeric"
            min={0}
            placeholder="0"
            value={minSalary}
            onChange={(event) => setMinSalary(event.target.value)}
          />
        </FilterField>
        <FilterField
          label={`Max salary (${reference?.base_currency ?? "USD"})`}
          id="filter-max-salary"
        >
          <Input
            id="filter-max-salary"
            type="number"
            inputMode="numeric"
            min={0}
            placeholder="No limit"
            value={maxSalary}
            onChange={(event) => setMaxSalary(event.target.value)}
          />
        </FilterField>
      </div>
    </div>
  );
}

function FilterField({
  label,
  id,
  children,
}: {
  label: string;
  id: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="text-xs text-muted-foreground">
        {label}
      </Label>
      {children}
    </div>
  );
}
