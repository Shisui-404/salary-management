"use client";

import { Info, ScaleIcon } from "lucide-react";
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
import { useAnalyticsPayEquity } from "@/hooks/use-analytics";
import { formatMoney, formatPercent, humanizeEnum } from "@/lib/format";

export function PayEquityPanel() {
  const query = useAnalyticsPayEquity();
  const data = query.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ScaleIcon className="size-4" aria-hidden="true" />
          Pay equity ({humanizeEnum(data?.overall?.comparison ?? "comparison")} vs{" "}
          {humanizeEnum(data?.overall?.reference ?? "reference")})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => query.refetch()}
            title="Couldn't load pay equity"
          />
        ) : query.isLoading || !data ? (
          <div className="space-y-4">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : !data.overall ? (
          <div className="rounded-lg border border-dashed p-8 text-center">
            <p className="text-sm font-medium">Not enough data to compare</p>
            <p className="mt-1 text-sm text-muted-foreground">
              A pay gap needs employees on both sides of the comparison. This
              view has none for at least one group
              {data.suppressed_groups > 0 ? (
                <>
                  , and {data.suppressed_groups} role/level group
                  {data.suppressed_groups === 1 ? " was" : "s were"} suppressed
                  for having fewer than {data.min_sample_size} employees
                </>
              ) : null}
              .
            </p>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-baseline gap-3 rounded-lg border bg-muted/40 p-4">
              <span className="text-3xl font-semibold tabular-nums">
                {formatPercent(data.overall.gap_pct, { withSign: true })}
              </span>
              <p className="text-sm text-muted-foreground">
                {humanizeEnum(data.overall.comparison)} employees earn a median{" "}
                {formatMoney(data.overall.comparison_median, data.base_currency)},
                vs {formatMoney(data.overall.reference_median, data.base_currency)}{" "}
                for {humanizeEnum(data.overall.reference)} (
                {data.overall.sample_comparison.toLocaleString()} vs{" "}
                {data.overall.sample_reference.toLocaleString()} employees).
              </p>
            </div>

            <div className="overflow-x-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Role · level</TableHead>
                    <TableHead className="text-right">
                      {humanizeEnum(data.overall.reference)} median
                    </TableHead>
                    <TableHead className="text-right">
                      {humanizeEnum(data.overall.comparison)} median
                    </TableHead>
                    <TableHead className="text-right">Gap</TableHead>
                    <TableHead className="text-right">Sample</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.groups.length === 0 ? (
                    <TableRow className="hover:bg-transparent">
                      <TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">
                        No group has a large enough sample to report.
                      </TableCell>
                    </TableRow>
                  ) : (
                    data.groups.map((group) => (
                      <TableRow key={group.key}>
                        <TableCell className="font-medium">{group.key}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(group.reference_median, data.base_currency)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(group.comparison_median, data.base_currency)}
                        </TableCell>
                        <TableCell
                          className={
                            "text-right font-medium tabular-nums " +
                            (group.gap_pct > 0
                              ? "text-destructive"
                              : "text-emerald-700 dark:text-emerald-400")
                          }
                        >
                          {formatPercent(group.gap_pct, { withSign: true })}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground tabular-nums">
                          {group.sample_reference} / {group.sample_comparison}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
              {data.suppressed_groups > 0 ? (
                <span>
                  {data.suppressed_groups} role/level group
                  {data.suppressed_groups === 1 ? "" : "s"} suppressed from this
                  table because one side had fewer than {data.min_sample_size}{" "}
                  employees — small samples produce misleading percentages, so
                  they&apos;re excluded rather than shown with false precision.
                </span>
              ) : (
                <span>
                  Groups with fewer than {data.min_sample_size} employees on
                  either side are excluded to avoid misleading percentages.
                </span>
              )}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
