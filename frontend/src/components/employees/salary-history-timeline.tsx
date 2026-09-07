import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/empty-state";
import type { SalaryRecord } from "@/lib/api/types";
import { formatDate, formatMoney, formatPercent, humanizeEnum } from "@/lib/format";
import { History, TrendingDown, TrendingUp } from "lucide-react";

const REASON_VARIANT: Record<
  SalaryRecord["change_reason"],
  "default" | "secondary" | "outline"
> = {
  initial: "outline",
  annual_review: "secondary",
  promotion: "default",
  market_adjustment: "secondary",
  role_change: "secondary",
  correction: "outline",
};

export function SalaryHistoryTimeline({ records }: { records: SalaryRecord[] }) {
  if (records.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="No salary history yet"
        description="Record a raise to start this employee's compensation timeline."
      />
    );
  }

  return (
    <ol className="relative space-y-6 border-l pl-6">
      {records.map((record) => (
        <li key={record.id} className="relative">
          <span
            className="absolute top-1.5 -left-[29px] size-2.5 rounded-full border-2 border-background bg-primary"
            aria-hidden="true"
          />
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold tabular-nums">
              {formatMoney(record.amount, record.currency)}
            </span>
            <Badge variant={REASON_VARIANT[record.change_reason]}>
              {humanizeEnum(record.change_reason)}
            </Badge>
            {record.change_pct !== null && (
              <span
                className={
                  "inline-flex items-center gap-0.5 text-xs font-medium tabular-nums " +
                  (record.change_pct >= 0
                    ? "text-emerald-700 dark:text-emerald-400"
                    : "text-destructive")
                }
              >
                {record.change_pct >= 0 ? (
                  <TrendingUp className="size-3" aria-hidden="true" />
                ) : (
                  <TrendingDown className="size-3" aria-hidden="true" />
                )}
                {formatPercent(record.change_pct, { withSign: true })}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {formatDate(record.effective_from)} –{" "}
            {record.effective_to ? formatDate(record.effective_to) : "Present"}
          </p>
          {record.currency !== record.base_currency && (
            <p className="text-xs text-muted-foreground tabular-nums">
              {formatMoney(record.amount_base, record.base_currency)} base
            </p>
          )}
          {record.note && (
            <p className="mt-1 text-sm text-muted-foreground italic">
              &ldquo;{record.note}&rdquo;
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}
