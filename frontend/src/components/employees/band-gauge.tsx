import type { Band } from "@/lib/api/types";
import { formatMoneyCompact } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Visual min/mid/max band gauge with the employee's current salary marked
 * on it. Percent position is computed from the decimal-string amounts via
 * `Number()` purely to place a marker on screen (a geometry problem, not a
 * money calculation) — nothing here feeds back into a financial figure.
 */
export function BandGauge({
  band,
  amountBase,
  baseCurrency,
}: {
  band: Band;
  amountBase: string;
  baseCurrency: string;
}) {
  const min = Number(band.min);
  const mid = Number(band.mid);
  const max = Number(band.max);
  const value = Number(amountBase);
  const range = max - min;
  const rawPercent = range > 0 ? ((value - min) / range) * 100 : 50;
  const clampedPercent = Math.min(100, Math.max(0, rawPercent));
  const midPercent = range > 0 ? ((mid - min) / range) * 100 : 50;
  const isOutOfRange = rawPercent < 0 || rawPercent > 100;

  return (
    <div className="space-y-2">
      <div className="relative pt-5">
        <div
          className="relative h-3 rounded-full bg-gradient-to-r from-amber-200 via-emerald-200 to-sky-200 dark:from-amber-500/25 dark:via-emerald-500/25 dark:to-sky-500/25"
          role="img"
          aria-label={`Salary band position: ${formatMoneyCompact(amountBase, baseCurrency)} within a band of ${formatMoneyCompact(band.min, baseCurrency)} to ${formatMoneyCompact(band.max, baseCurrency)}, midpoint ${formatMoneyCompact(band.mid, baseCurrency)}.`}
        >
          {/* Midpoint tick */}
          <div
            className="absolute top-0 h-full w-px bg-foreground/30"
            style={{ left: `${midPercent}%` }}
          />
          {/* Employee marker */}
          <div
            className={cn(
              "absolute top-1/2 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center",
            )}
            style={{ left: `${clampedPercent}%` }}
          >
            <div
              className={cn(
                "size-4 rounded-full border-2 border-background shadow-sm",
                isOutOfRange ? "bg-destructive" : "bg-foreground",
              )}
              title={formatMoneyCompact(amountBase, baseCurrency)}
            />
          </div>
        </div>
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Min {formatMoneyCompact(band.min, baseCurrency)}</span>
        <span>Mid {formatMoneyCompact(band.mid, baseCurrency)}</span>
        <span>Max {formatMoneyCompact(band.max, baseCurrency)}</span>
      </div>
    </div>
  );
}
