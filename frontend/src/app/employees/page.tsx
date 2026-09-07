import { Suspense } from "react";
import { EmployeesPageClient } from "@/components/employees/employees-page-client";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata = {
  title: "Employees · ACME Compensation",
};

function EmployeesPageFallback() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-9 w-48" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-96 w-full" />
    </div>
  );
}

export default function EmployeesPage() {
  return (
    <Suspense fallback={<EmployeesPageFallback />}>
      <EmployeesPageClient />
    </Suspense>
  );
}
