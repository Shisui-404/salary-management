import { Users, Wallet, TrendingUp, ShieldCheck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { AnalyticsSummary } from "@/lib/api/types";
import { formatMoneyCompact, formatPercent } from "@/lib/format";

interface KpiCardsProps {
  summary?: AnalyticsSummary;
  isLoading: boolean;
}

export function KpiCards({ summary, isLoading }: KpiCardsProps) {
  const items = [
    {
      label: "Headcount",
      icon: Users,
      value: summary
        ? `${summary.headcount.toLocaleString()}`
        : undefined,
      hint: summary
        ? `${summary.active_headcount.toLocaleString()} active · ${summary.countries} countries`
        : undefined,
    },
    {
      label: "Total annual payroll",
      icon: Wallet,
      value: summary
        ? formatMoneyCompact(summary.total_annual_payroll, summary.base_currency)
        : undefined,
      hint: summary ? `${summary.base_currency}, normalised` : undefined,
    },
    {
      label: "Median salary",
      icon: TrendingUp,
      value: summary
        ? formatMoneyCompact(summary.median_salary, summary.base_currency)
        : undefined,
      hint: summary
        ? `Mean ${formatMoneyCompact(summary.mean_salary, summary.base_currency)}`
        : undefined,
    },
    {
      label: "Band coverage",
      icon: ShieldCheck,
      value: summary ? formatPercent(summary.band_coverage_pct) : undefined,
      hint: summary ? `${summary.departments} departments` : undefined,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label}>
          <CardContent className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs text-muted-foreground">{item.label}</p>
              {isLoading || !item.value ? (
                <Skeleton className="mt-1.5 h-7 w-20" />
              ) : (
                <p className="mt-0.5 text-2xl font-semibold tabular-nums">
                  {item.value}
                </p>
              )}
              {isLoading || !item.hint ? (
                <Skeleton className="mt-2 h-3 w-28" />
              ) : (
                <p className="mt-1 text-xs text-muted-foreground">{item.hint}</p>
              )}
            </div>
            <item.icon
              className="size-5 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
