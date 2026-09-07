import type { BandPosition } from "@/lib/api/types";

/**
 * Formats a decimal-string amount (as delivered by the API — never a JSON
 * number) as localised currency. `Intl.NumberFormat` parses the string via
 * `Number()` internally for display only; we never do arithmetic on it here.
 */
export function formatMoney(
  amount: string | number,
  currency: string,
  options: Intl.NumberFormatOptions = {},
): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  if (Number.isNaN(value)) return "—";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
      ...options,
    }).format(value);
  } catch {
    // Unknown/invalid ISO currency code — fall back to a plain number so the
    // UI never crashes on unexpected reference data.
    return `${value.toLocaleString()} ${currency}`;
  }
}

/** Compact currency form for dense contexts (KPI tiles, chart axes). */
export function formatMoneyCompact(
  amount: string | number,
  currency: string,
): string {
  return formatMoney(amount, currency, {
    notation: "compact",
    maximumFractionDigits: 1,
  });
}

/** Percentages: always one decimal place, per the quality bar. */
export function formatPercent(
  value: number | null | undefined,
  options: { withSign?: boolean } = {},
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const formatted = value.toFixed(1);
  if (options.withSign && value > 0) {
    return `+${formatted}%`;
  }
  return `${formatted}%`;
}

/** Compa-ratio (e.g. 0.98) formatted as "0.98x". */
export function formatCompaRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${value.toFixed(2)}x`;
}

export type BadgeVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "outline";

/**
 * Maps a compa-ratio to a badge variant so the directory/profile agree on
 * one visual language: notably under-band (<0.8) and notably over-band
 * (>1.2) are flagged for attention, the broad "on target" band reads as
 * neutral.
 */
export function compaRatioToBadgeVariant(
  compaRatio: number | null | undefined,
): BadgeVariant {
  if (compaRatio === null || compaRatio === undefined) return "outline";
  if (compaRatio < 0.8 || compaRatio > 1.2) return "destructive";
  if (compaRatio < 0.9 || compaRatio > 1.1) return "secondary";
  return "default";
}

/** Tailwind classes for a band-position badge/dot — one palette, everywhere. */
export function bandPositionToColorClasses(position: BandPosition): string {
  switch (position) {
    case "below":
      return "bg-amber-100 text-amber-900 dark:bg-amber-500/15 dark:text-amber-300";
    case "within":
      return "bg-emerald-100 text-emerald-900 dark:bg-emerald-500/15 dark:text-emerald-300";
    case "above":
      return "bg-sky-100 text-sky-900 dark:bg-sky-500/15 dark:text-sky-300";
    case "unbanded":
    default:
      return "bg-muted text-muted-foreground";
  }
}

export function bandPositionLabel(position: BandPosition): string {
  switch (position) {
    case "below":
      return "Below band";
    case "within":
      return "Within band";
    case "above":
      return "Above band";
    case "unbanded":
    default:
      return "Unbanded";
  }
}

/** Human label for enum-ish values like `annual_review` -> "Annual review". */
export function humanizeEnum(value: string): string {
  const spaced = value.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
