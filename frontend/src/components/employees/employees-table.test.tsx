import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { employeeFixtures } from "@/lib/fixtures/employees";
import { EmployeesTable } from "./employees-table";

describe("EmployeesTable", () => {
  it("renders one row per employee fixture, with name, department and band position", () => {
    render(
      <EmployeesTable
        data={employeeFixtures}
        isLoading={false}
        sort="name"
        sortDir="asc"
        onSortChange={vi.fn()}
      />,
    );

    for (const employee of employeeFixtures) {
      const link = screen.getByRole("link", { name: employee.full_name });
      expect(link).toHaveAttribute("href", `/employees/${employee.id}`);

      const row = link.closest("tr");
      expect(row).not.toBeNull();
      expect(within(row as HTMLElement).getByText(employee.department.name)).toBeInTheDocument();
    }
  });

  it("shows an employee with no salary record as such, rather than $0", () => {
    render(
      <EmployeesTable
        data={employeeFixtures}
        isLoading={false}
        sort="name"
        sortDir="asc"
        onSortChange={vi.fn()}
      />,
    );

    expect(screen.getByText("No salary record")).toBeInTheDocument();
  });

  it("renders skeleton rows instead of data while loading", () => {
    const { container } = render(
      <EmployeesTable
        data={[]}
        isLoading
        sort="name"
        sortDir="asc"
        onSortChange={vi.fn()}
      />,
    );

    expect(screen.queryByText(employeeFixtures[0].full_name)).not.toBeInTheDocument();
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it("shows an empty state when there is no data and it isn't loading", () => {
    render(
      <EmployeesTable
        data={[]}
        isLoading={false}
        sort="name"
        sortDir="asc"
        onSortChange={vi.fn()}
      />,
    );

    expect(
      screen.getByText("No employees match these filters"),
    ).toBeInTheDocument();
  });
});
