"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/error-state";
import type { AnalyticsDistribution } from "@/lib/api/types";
import { formatMoneyCompact } from "@/lib/format";
import { CHART_COLORS } from "@/lib/chart-colors";

interface DistributionChartProps {
  data?: AnalyticsDistribution;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
}

interface ChartRow {
  label: string;
  count: number;
}

const PERCENTILE_LABELS: { key: keyof AnalyticsDistribution["percentiles"]; label: string }[] = [
  { key: "p10", label: "P10" },
  { key: "p25", label: "P25" },
  { key: "p50", label: "Median (P50)" },
  { key: "p75", label: "P75" },
  { key: "p90", label: "P90" },
];

export function DistributionChart({
  data,
  isLoading,
  error,
  onRetry,
}: DistributionChartProps) {
  const rows: ChartRow[] =
    data?.histogram.map((bucket) => ({
      label: `${formatMoneyCompact(bucket.lower, data.base_currency)}–${formatMoneyCompact(bucket.upper, data.base_currency)}`,
      count: bucket.count,
    })) ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Salary distribution</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error ? (
          <ErrorState error={error} onRetry={onRetry} title="Couldn't load the distribution" />
        ) : isLoading || !data ? (
          <Skeleton className="h-72 w-full" />
        ) : (
          <>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rows} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke={CHART_COLORS.grid}
                    vertical={false}
                  />
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 11, fill: CHART_COLORS.axis }}
                    tickLine={false}
                    axisLine={{ stroke: CHART_COLORS.grid }}
                    interval={Math.max(0, Math.floor(rows.length / 6) - 1)}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: CHART_COLORS.axis }}
                    tickLine={false}
                    axisLine={false}
                    width={40}
                  />
                  <Tooltip
                    cursor={{ fill: "var(--muted)" }}
                    contentStyle={{
                      background: "var(--popover)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    formatter={(value) => [
                      `${Number(value).toLocaleString()} employees`,
                      "Count",
                    ]}
                  />
                  <Bar
                    dataKey="count"
                    fill={CHART_COLORS.series1}
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div
              className="grid grid-cols-2 gap-3 border-t pt-4 sm:grid-cols-5"
              aria-label="Salary percentiles"
            >
              {PERCENTILE_LABELS.map(({ key, label }) => (
                <div key={key}>
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="text-sm font-semibold tabular-nums">
                    {formatMoneyCompact(data.percentiles[key], data.base_currency)}
                  </p>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
