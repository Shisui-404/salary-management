"use client";

import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import type { Employee, SortField } from "@/lib/api/types";
import { EmptyState } from "@/components/shared/empty-state";
import { Users } from "lucide-react";
import { employeeColumns, SORTABLE_COLUMNS } from "./columns";

interface EmployeesTableProps {
  data: Employee[];
  isLoading: boolean;
  sort: SortField;
  sortDir: "asc" | "desc";
  onSortChange: (field: SortField) => void;
}

const SKELETON_ROWS = 10;

export function EmployeesTable({
  data,
  isLoading,
  sort,
  sortDir,
  onSortChange,
}: EmployeesTableProps) {
  const table = useReactTable({
    data,
    columns: employeeColumns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="overflow-x-auto">
      <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const sortField = SORTABLE_COLUMNS[header.column.id];
                  const isActive = sortField === sort;
                  return (
                    <TableHead key={header.id} className="whitespace-nowrap">
                      {sortField ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="-ml-3 h-8 gap-1.5 px-3 font-medium"
                          onClick={() => onSortChange(sortField)}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                          {isActive ? (
                            sortDir === "asc" ? (
                              <ArrowUp className="size-3.5" aria-hidden="true" />
                            ) : (
                              <ArrowDown className="size-3.5" aria-hidden="true" />
                            )
                          ) : (
                            <ArrowUpDown
                              className="size-3.5 text-muted-foreground/50"
                              aria-hidden="true"
                            />
                          )}
                        </Button>
                      ) : (
                        flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: SKELETON_ROWS }).map((_, rowIndex) => (
                <TableRow key={`skeleton-${rowIndex}`}>
                  {employeeColumns.map((column) => (
                    <TableCell key={column.id}>
                      <Skeleton className="h-5 w-full max-w-32" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : data.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={employeeColumns.length} className="py-10">
                  <EmptyState
                    icon={Users}
                    title="No employees match these filters"
                    description="Try widening your search or clearing a filter."
                  />
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
    </div>
  );
}
