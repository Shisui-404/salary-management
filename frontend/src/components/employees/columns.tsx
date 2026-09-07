"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { Employee, SortField } from "@/lib/api/types";
import {
  compaRatioToBadgeVariant,
  formatCompaRatio,
  formatMoney,
} from "@/lib/format";
import { BandPositionBadge } from "./band-position-badge";

/** Marks the columns whose header the API can sort by (`sort` query param). */
export const SORTABLE_COLUMNS: Record<string, SortField> = {
  full_name: "name",
  department: "department",
  hire_date: "hire_date",
  salary: "salary",
  compa_ratio: "compa_ratio",
};

export const employeeColumns: ColumnDef<Employee>[] = [
  {
    id: "full_name",
    header: "Name",
    cell: ({ row }) => {
      const employee = row.original;
      return (
        <div className="flex flex-col">
          <Link
            href={`/employees/${employee.id}`}
            className="font-medium text-foreground hover:underline"
          >
            {employee.full_name}
          </Link>
          <span className="text-xs text-muted-foreground">
            {employee.employee_code}
          </span>
        </div>
      );
    },
  },
  {
    id: "department",
    header: "Department",
    cell: ({ row }) => row.original.department.name,
  },
  {
    id: "job_role",
    header: "Role",
    cell: ({ row }) => row.original.job_role.name,
  },
  {
    id: "level",
    header: "Level",
    cell: ({ row }) => row.original.level.name,
  },
  {
    id: "country",
    header: "Country",
    cell: ({ row }) => (
      <span title={row.original.country.name}>
        {row.original.country.code}
      </span>
    ),
  },
  {
    id: "salary",
    header: "Salary",
    cell: ({ row }) => {
      const salary = row.original.current_salary;
      if (!salary) {
        return <span className="text-muted-foreground">No salary record</span>;
      }
      const sameCurrency = salary.currency === salary.base_currency;
      return (
        <div className="flex flex-col">
          <span className="font-medium tabular-nums">
            {formatMoney(salary.amount, salary.currency)}
          </span>
          {!sameCurrency && (
            <span className="text-xs text-muted-foreground tabular-nums">
              {formatMoney(salary.amount_base, salary.base_currency)} base
            </span>
          )}
        </div>
      );
    },
  },
  {
    id: "compa_ratio",
    header: "Compa-ratio",
    cell: ({ row }) => {
      const value = row.original.compa_ratio;
      return (
        <Badge variant={compaRatioToBadgeVariant(value)} className="tabular-nums">
          {formatCompaRatio(value)}
        </Badge>
      );
    },
  },
  {
    id: "band_position",
    header: "Band",
    cell: ({ row }) => <BandPositionBadge position={row.original.band_position} />,
  },
];
