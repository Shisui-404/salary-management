/**
 * Chart color roles. `series1`/`series2` reference the validated categorical
 * tokens in globals.css (`--chart-1`/`--chart-2` — blue/orange, fixed hue
 * order, never reassigned per render).
 *
 * `below`/`within`/`above`/`unbanded` intentionally reuse the same hexes as
 * `bandPositionToColorClasses` in `src/lib/format.ts` (Tailwind's
 * amber/emerald/sky/slate-400) rather than the dataviz skill's separate
 * status palette — the chart and the badges encode the same concept and
 * must look like the same concept.
 */
export const CHART_COLORS = {
  series1: "var(--chart-1)",
  series2: "var(--chart-2)",
  below: "#f59e0b",
  within: "#10b981",
  above: "#0ea5e9",
  unbanded: "#94a3b8",
  grid: "var(--border)",
  axis: "var(--muted-foreground)",
} as const;
