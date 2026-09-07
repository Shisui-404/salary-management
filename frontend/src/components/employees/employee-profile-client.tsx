"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { ErrorState } from "@/components/shared/error-state";
import { useEmployee, useSalaryHistory } from "@/hooks/use-employees";
import { useReference } from "@/hooks/use-reference";
import type { ChangeReason, Employee, EmploymentStatus } from "@/lib/api/types";
import { formatDate, humanizeEnum } from "@/lib/format";
import { CurrentCompensationCard } from "./current-compensation-card";
import { RecordRaiseDialog } from "./record-raise-dialog";
import { SalaryHistoryTimeline } from "./salary-history-timeline";

const STATUS_VARIANT: Record<
  EmploymentStatus,
  "default" | "secondary" | "outline"
> = {
  active: "default",
  on_leave: "secondary",
  terminated: "outline",
};

export function EmployeeProfileClient({ employeeId }: { employeeId: number }) {
  const employeeQuery = useEmployee(employeeId);
  const historyQuery = useSalaryHistory(employeeId);
  const referenceQuery = useReference();

  return (
    <div className="flex flex-col gap-6">
      <Button
        variant="ghost"
        size="sm"
        className="w-fit -ml-2"
        render={<Link href="/employees" />}
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to employees
      </Button>

      {employeeQuery.isLoading ? (
        <ProfileSkeleton />
      ) : employeeQuery.isError ? (
        <ErrorState
          error={employeeQuery.error}
          onRetry={() => employeeQuery.refetch()}
          title="Couldn't load this employee"
        />
      ) : employeeQuery.data ? (
        <ProfileBody
          employee={employeeQuery.data}
          changeReasons={referenceQuery.data?.change_reasons ?? []}
          historySection={
            historyQuery.isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : historyQuery.isError ? (
              <ErrorState
                error={historyQuery.error}
                onRetry={() => historyQuery.refetch()}
                title="Couldn't load salary history"
              />
            ) : (
              <SalaryHistoryTimeline records={historyQuery.data?.items ?? []} />
            )
          }
        />
      ) : null}
    </div>
  );
}

function ProfileBody({
  employee,
  changeReasons,
  historySection,
}: {
  employee: Employee;
  changeReasons: ChangeReason[];
  historySection: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-lg border bg-card p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">
              {employee.full_name}
            </h1>
            <Badge variant={STATUS_VARIANT[employee.employment_status]}>
              {humanizeEnum(employee.employment_status)}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {employee.job_role.name} · {employee.level.name} ·{" "}
            {employee.department.name} · {employee.country.name}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {employee.employee_code} · {employee.email}
          </p>
        </div>
        <RecordRaiseDialog
          employeeId={employee.id}
          currentSalary={employee.current_salary}
          changeReasons={
            changeReasons.length > 0
              ? changeReasons
              : [
                  "initial",
                  "annual_review",
                  "promotion",
                  "market_adjustment",
                  "role_change",
                  "correction",
                ]
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <CurrentCompensationCard employee={employee} />
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Employment details</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3 text-sm">
              <DetailRow label="Hire date" value={formatDate(employee.hire_date)} />
              <DetailRow label="Department" value={employee.department.name} />
              <DetailRow label="Job role" value={employee.job_role.name} />
              <DetailRow label="Level" value={employee.level.name} />
              <DetailRow
                label="Country"
                value={`${employee.country.name} (${employee.country.code})`}
              />
              <DetailRow label="Gender" value={humanizeEnum(employee.gender)} />
              <DetailRow
                label="Manager"
                value={
                  employee.manager_id
                    ? `Employee #${employee.manager_id}`
                    : "—"
                }
              />
            </dl>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Salary history</CardTitle>
        </CardHeader>
        <CardContent>
          <Separator className="mb-4" />
          {historySection}
        </CardContent>
      </Card>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-24 w-full" />
      <div className="grid gap-6 lg:grid-cols-3">
        <Skeleton className="h-64 lg:col-span-2" />
        <Skeleton className="h-64" />
      </div>
      <Skeleton className="h-72 w-full" />
    </div>
  );
}
