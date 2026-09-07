import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CurrentSalary } from "@/lib/api/types";
import { RecordRaiseDialog } from "./record-raise-dialog";

const recordSalaryMock = vi.fn();

vi.mock("@/lib/api/employees", () => ({
  recordSalary: (...args: unknown[]) => recordSalaryMock(...args),
}));

const currentSalary: CurrentSalary = {
  amount: "2400000.00",
  currency: "INR",
  amount_base: "28800.00",
  base_currency: "USD",
  effective_from: "2024-04-01",
  change_reason: "annual_review",
};

function renderDialog() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RecordRaiseDialog
        employeeId={1}
        currentSalary={currentSalary}
        changeReasons={["annual_review", "promotion", "correction"]}
      />
    </QueryClientProvider>,
  );
}

describe("RecordRaiseDialog", () => {
  afterEach(() => {
    recordSalaryMock.mockReset();
  });

  it("blocks submission when the effective date is not after the current record's", async () => {
    const user = userEvent.setup();
    renderDialog();

    await user.click(screen.getByRole("button", { name: /record a raise/i }));

    const amountInput = await screen.findByLabelText(/new amount/i);
    await user.type(amountInput, "2650000.00");

    const dateInput = screen.getByLabelText(/effective from/i);
    await user.clear(dateInput);
    // Same date as the current record's effective_from — the API's
    // salary_effective_date_invalid rule requires strictly after.
    await user.type(dateInput, "2024-04-01");

    await user.click(screen.getByRole("button", { name: /save raise/i }));

    expect(
      await screen.findByText(/must be after the current record's effective date/i),
    ).toBeInTheDocument();
    expect(recordSalaryMock).not.toHaveBeenCalled();
  });

  it("submits successfully once the effective date is valid", async () => {
    recordSalaryMock.mockResolvedValue({
      id: 999,
      employee_id: 1,
      amount: "2650000.00",
      currency: "INR",
      amount_base: "31500.00",
      base_currency: "USD",
      effective_from: "2025-04-01",
      effective_to: null,
      change_reason: "annual_review",
      note: null,
      created_at: "2025-03-01T00:00:00Z",
      change_pct: 10.4,
    });

    const user = userEvent.setup();
    renderDialog();

    await user.click(screen.getByRole("button", { name: /record a raise/i }));

    const amountInput = await screen.findByLabelText(/new amount/i);
    await user.type(amountInput, "2650000.00");

    const dateInput = screen.getByLabelText(/effective from/i);
    await user.clear(dateInput);
    await user.type(dateInput, "2025-04-01");

    await user.click(screen.getByRole("button", { name: /save raise/i }));

    await waitFor(() => expect(recordSalaryMock).toHaveBeenCalledTimes(1));
    expect(recordSalaryMock).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        amount: "2650000.00",
        currency: "INR",
        effective_from: "2025-04-01",
      }),
    );
  });
});
