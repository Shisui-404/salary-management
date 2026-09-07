"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/error-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAnalyticsBandHealth } from "@/hooks/use-analytics";
import { formatCompaRatio, formatMoney, formatPercent } from "@/lib/format";
import { CHART_COLORS } from "@/lib/chart-colors";
import { BandPositionBadge } from "@/components/employees/band-position-badge";
import type { AnalyticsBandHealth } from "@/lib/api/types";

const SEGMENTS: {
  key: keyof Pick<AnalyticsBandHealth, "below" | "within" | "above" | "unbanded">;
  pctKey: "below_pct" | "within_pct" | "above_pct" | null;
  label: string;
  color: string;
}[] = [
  { key: "below", pctKey: "below_pct", label: "Below band", color: CHART_COLORS.below },
  { key: "within", pctKey: "within_pct", label: "Within band", color: CHART_COLORS.within },
  { key: "above", pctKey: "above_pct", label: "Above band", color: CHART_COLORS.above },
  { key: "unbanded", pctKey: null, label: "Unbanded", color: CHART_COLORS.unbanded },
];

export function BandHealthPanel() {
  const query = useAnalyticsBandHealth();
  const data = query.data;
  const total = data
    ? data.below + data.within + data.above + data.unbanded
    : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Band health</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => query.refetch()}
            title="Couldn't load band health"
          />
        ) : query.isLoading || !data ? (
          <div className="space-y-4">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        ) : (
          <>
            <div>
              <div
                className="flex h-3 w-full overflow-hidden rounded-full"
                role="img"
                aria-label={`${data.below_pct.toFixed(1)}% below band, ${data.within_pct.toFixed(1)}% within band, ${data.above_pct.toFixed(1)}% above band, ${total > 0 ? ((data.unbanded / total) * 100).toFixed(1) : "0"}% unbanded.`}
              >
                {SEGMENTS.map((segment) => {
                  const count = data[segment.key];
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  if (pct === 0) return null;
                  return (
                    <div
                      key={segment.key}
                      style={{ width: `${pct}%`, backgroundColor: segment.color }}
                      title={`${segment.label}: ${count.toLocaleString()}`}
                    />
                  );
                })}
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                {SEGMENTS.map((segment) => (
                  <div key={segment.key} className="flex items-center gap-2">
                    <span
                      className="size-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: segment.color }}
                      aria-hidden="true"
                    />
                    <div>
                      <p className="text-xs text-muted-foreground">{segment.label}</p>
                      <p className="text-sm font-semibold tabular-nums">
                        {data[segment.key].toLocaleString()}
                        {segment.pctKey && (
                          <span className="ml-1 font-normal text-muted-foreground">
                            ({formatPercent(data[segment.pctKey])})
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium">
                Largest outliers ({data.outliers.length})
              </p>
              <div className="overflow-x-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>Role · level</TableHead>
                      <TableHead>Country</TableHead>
                      <TableHead className="text-right">Salary</TableHead>
                      <TableHead className="text-right">Compa-ratio</TableHead>
                      <TableHead className="text-right">Deviation</TableHead>
                      <TableHead>Position</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.outliers.length === 0 ? (
                      <TableRow className="hover:bg-transparent">
                        <TableCell colSpan={7} className="py-8 text-center text-sm text-muted-foreground">
                          No band outliers — everyone with a band is within it.
                        </TableCell>
                      </TableRow>
                    ) : (
                      data.outliers.map((outlier) => (
                        <TableRow key={outlier.employee_id}>
                          <TableCell>
                            <Link
                              href={`/employees/${outlier.employee_id}`}
                              className="font-medium hover:underline"
                            >
                              {outlier.full_name}
                            </Link>
                            <p className="text-xs text-muted-foreground">
                              {outlier.department}
                            </p>
                          </TableCell>
                          <TableCell>
                            {outlier.job_role} · {outlier.level}
                          </TableCell>
                          <TableCell>{outlier.country}</TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatMoney(outlier.salary_base, data.base_currency)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatCompaRatio(outlier.compa_ratio)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatPercent(outlier.deviation_pct, { withSign: true })}
                          </TableCell>
                          <TableCell>
                            <BandPositionBadge position={outlier.position} />
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
