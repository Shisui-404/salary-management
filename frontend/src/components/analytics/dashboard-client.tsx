"use client";

import { PageHeader } from "@/components/shared/page-header";
import { useAnalyticsDistribution, useAnalyticsSummary } from "@/hooks/use-analytics";
import { KpiCards } from "./kpi-cards";
import { DistributionChart } from "./distribution-chart";
import { DimensionChart } from "./dimension-chart";
import { PayEquityPanel } from "./pay-equity-panel";
import { BandHealthPanel } from "./band-health-panel";

export function DashboardClient() {
  const summaryQuery = useAnalyticsSummary();
  const distributionQuery = useAnalyticsDistribution();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Compensation dashboard"
        description="How ACME pays people, across departments, countries and roles — normalised to a single base currency."
      />

      <KpiCards summary={summaryQuery.data} isLoading={summaryQuery.isLoading} />

      {summaryQuery.isError && (
        <p className="text-sm text-destructive">
          Some KPI tiles couldn&apos;t load: {(summaryQuery.error as Error).message}
        </p>
      )}

      <DistributionChart
        data={distributionQuery.data}
        isLoading={distributionQuery.isLoading}
        error={distributionQuery.error}
        onRetry={() => distributionQuery.refetch()}
      />

      <DimensionChart />

      <PayEquityPanel />
      <BandHealthPanel />
    </div>
  );
}
