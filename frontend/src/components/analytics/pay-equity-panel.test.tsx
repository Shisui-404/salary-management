import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { payEquityFixture } from "@/lib/fixtures/analytics";
import type { AnalyticsPayEquity } from "@/lib/api/types";

const useAnalyticsPayEquity = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/use-analytics", () => ({ useAnalyticsPayEquity }));

const { PayEquityPanel } = await import("./pay-equity-panel");

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function renderWith(data: AnalyticsPayEquity | undefined, overrides = {}) {
  useAnalyticsPayEquity.mockReturnValue({
    data,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  });
  return render(<PayEquityPanel />, { wrapper });
}

describe("PayEquityPanel", () => {
  it("renders the headline gap when both sides of the comparison have data", () => {
    renderWith(payEquityFixture);
    expect(screen.getByText(/employees earn a median/i)).toBeInTheDocument();
  });

  it("does not crash when `overall` is null, and explains why", () => {
    // The API returns overall: null whenever one side of the comparison is
    // empty -- e.g. filtered to a single gender. Reproduced live against the
    // backend as: {"overall":null,"groups":[],"suppressed_groups":138}.
    renderWith({
      ...payEquityFixture,
      overall: null,
      groups: [],
      suppressed_groups: 138,
    });

    expect(screen.getByText(/not enough data to compare/i)).toBeInTheDocument();
    expect(screen.getByText(/138 role\/level groups were suppressed/i)).toBeInTheDocument();
    expect(screen.queryByText(/employees earn a median/i)).not.toBeInTheDocument();
  });

  it("handles a null `overall` with no suppressed groups either", () => {
    renderWith({
      ...payEquityFixture,
      overall: null,
      groups: [],
      suppressed_groups: 0,
    });
    expect(screen.getByText(/not enough data to compare/i)).toBeInTheDocument();
  });
});
