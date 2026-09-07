"use client";

import { useState } from "react";
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAnalyticsByDimension } from "@/hooks/use-analytics";
import type { Dimension } from "@/lib/api/types";
import { formatMoneyCompact } from "@/lib/format";
import { CHART_COLORS } from "@/lib/chart-colors";

const DIMENSIONS: { value: Dimension; label: string }[] = [
  { value: "department", label: "Department" },
  { value: "country", label: "Country" },
  { value: "job_role", label: "Job role" },
  { value: "level", label: "Level" },
];

interface TooltipPayloadItem {
  payload: { name: string; median: number; headcount: number };
}

export function DimensionChart() {
  const [dimension, setDimension] = useState<Dimension>("department");
  const query = useAnalyticsByDimension(dimension);
  const data = query.data;

  const rows =
    data?.groups.map((group) => ({
      name: group.name,
      median: Number(group.median),
      headcount: group.headcount,
    })) ?? [];

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle>Median salary by {DIMENSIONS.find((d) => d.value === dimension)?.label.toLowerCase()}</CardTitle>
        <Tabs value={dimension} onValueChange={(v) => setDimension(v as Dimension)}>
          <TabsList>
            {DIMENSIONS.map((d) => (
              <TabsTrigger key={d.value} value={d.value}>
                {d.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent>
        {query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => query.refetch()}
            title="Couldn't load this breakdown"
          />
        ) : query.isLoading || !data ? (
          <Skeleton className="h-80 w-full" />
        ) : rows.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            No data for this dimension.
          </p>
        ) : (
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={rows}
                layout="vertical"
                margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke={CHART_COLORS.grid}
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: CHART_COLORS.axis }}
                  tickLine={false}
                  axisLine={{ stroke: CHART_COLORS.grid }}
                  tickFormatter={(v: number) => formatMoneyCompact(v, data.base_currency)}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 12, fill: CHART_COLORS.axis }}
                  tickLine={false}
                  axisLine={false}
                  width={140}
                />
                <Tooltip
                  cursor={{ fill: "var(--muted)" }}
                  contentStyle={{
                    background: "var(--popover)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const item = (payload[0] as TooltipPayloadItem).payload;
                    return (
                      <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
                        <p className="font-medium">{item.name}</p>
                        <p className="text-muted-foreground">
                          Median {formatMoneyCompact(item.median, data.base_currency)}
                        </p>
                        <p className="text-muted-foreground">
                          {item.headcount.toLocaleString()} employees
                        </p>
                      </div>
                    );
                  }}
                />
                <Bar dataKey="median" fill={CHART_COLORS.series1} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
