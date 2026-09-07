"use client";

import { useParams } from "next/navigation";
import { EmployeeProfileClient } from "@/components/employees/employee-profile-client";
import { ErrorState } from "@/components/shared/error-state";

export default function EmployeeProfilePage() {
  const params = useParams<{ id: string }>();
  const employeeId = Number(params.id);

  if (!Number.isFinite(employeeId)) {
    return (
      <ErrorState
        error={new Error(`"${params.id}" is not a valid employee id.`)}
        title="Invalid employee"
      />
    );
  }

  return <EmployeeProfileClient employeeId={employeeId} />;
}
