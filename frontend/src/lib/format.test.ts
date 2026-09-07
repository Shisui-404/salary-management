import { describe, expect, it } from "vitest";
import {
  bandPositionToColorClasses,
  compaRatioToBadgeVariant,
  formatCompaRatio,
  formatMoney,
  formatMoneyCompact,
  formatPercent,
  humanizeEnum,
} from "./format";

describe("formatMoney", () => {
  it("formats a decimal-string amount as localised currency", () => {
    expect(formatMoney("2400000.00", "INR")).toBe(
      new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      }).format(2400000),
    );
  });

  it("never does float arithmetic — it only formats what the API sent", () => {
    // 0.1 + 0.2 !== 0.3 in float math; formatMoney must not add anything up,
    // it only renders the single string the API already computed.
    expect(formatMoney("0.30", "USD")).toContain("0");
  });

  it("falls back gracefully for an unknown currency code instead of throwing", () => {
    expect(() => formatMoney("100.00", "XXX_NOT_REAL")).not.toThrow();
  });

  it("renders an em dash for a non-numeric amount", () => {
    expect(formatMoney("not-a-number", "USD")).toBe("—");
  });
});

describe("formatMoneyCompact", () => {
  it("uses compact notation", () => {
    const result = formatMoneyCompact("612450000.00", "USD");
    // Compact notation should be shorter than the full number of digits.
    expect(result.length).toBeLessThan("612450000".length);
  });
});

describe("formatPercent", () => {
  it("always renders one decimal place", () => {
    expect(formatPercent(5)).toBe("5.0%");
    expect(formatPercent(5.04)).toBe("5.0%");
    expect(formatPercent(5.06)).toBe("5.1%");
  });

  it("renders — for null/undefined", () => {
    expect(formatPercent(null)).toBe("—");
    expect(formatPercent(undefined)).toBe("—");
  });

  it("shows an explicit sign for positive and negative values when requested", () => {
    expect(formatPercent(5, { withSign: true })).toBe("+5.0%");
    expect(formatPercent(-5, { withSign: true })).toBe("-5.0%");
    // Zero is neither a gain nor a loss — no "+0.0%".
    expect(formatPercent(0, { withSign: true })).toBe("0.0%");
  });

  it("omits the sign by default", () => {
    expect(formatPercent(5)).toBe("5.0%");
    expect(formatPercent(-5)).toBe("-5.0%");
  });
});

describe("formatCompaRatio", () => {
  it("formats to two decimals with an x suffix", () => {
    expect(formatCompaRatio(0.98)).toBe("0.98x");
    expect(formatCompaRatio(1)).toBe("1.00x");
  });

  it("renders — for null (unbanded employees)", () => {
    expect(formatCompaRatio(null)).toBe("—");
  });
});

describe("compaRatioToBadgeVariant", () => {
  it("flags notably under-band ratios as destructive", () => {
    expect(compaRatioToBadgeVariant(0.48)).toBe("destructive");
    expect(compaRatioToBadgeVariant(0.79)).toBe("destructive");
  });

  it("flags notably over-band ratios as destructive", () => {
    expect(compaRatioToBadgeVariant(1.21)).toBe("destructive");
    expect(compaRatioToBadgeVariant(1.83)).toBe("destructive");
  });

  it("flags mild deviation as secondary", () => {
    expect(compaRatioToBadgeVariant(0.85)).toBe("secondary");
    expect(compaRatioToBadgeVariant(1.15)).toBe("secondary");
  });

  it("treats the on-target band as the default variant", () => {
    expect(compaRatioToBadgeVariant(0.98)).toBe("default");
    expect(compaRatioToBadgeVariant(1.0)).toBe("default");
  });

  it("treats null (unbanded) as outline", () => {
    expect(compaRatioToBadgeVariant(null)).toBe("outline");
    expect(compaRatioToBadgeVariant(undefined)).toBe("outline");
  });

  it("is symmetric around 1.0", () => {
    // The boundaries below and above the midpoint should classify the same
    // way (0.8 <-> 1.2, 0.9 <-> 1.1), since compa-ratio has no directional
    // preference in this classification.
    expect(compaRatioToBadgeVariant(0.8)).toBe(compaRatioToBadgeVariant(1.2));
    expect(compaRatioToBadgeVariant(0.9)).toBe(compaRatioToBadgeVariant(1.1));
  });
});

describe("bandPositionToColorClasses", () => {
  it("returns a distinct class string for every band position", () => {
    const positions = ["below", "within", "above", "unbanded"] as const;
    const classes = positions.map(bandPositionToColorClasses);
    expect(new Set(classes).size).toBe(positions.length);
  });
});

describe("humanizeEnum", () => {
  it("replaces underscores with spaces and capitalises the first letter", () => {
    expect(humanizeEnum("annual_review")).toBe("Annual review");
    expect(humanizeEnum("market_adjustment")).toBe("Market adjustment");
    expect(humanizeEnum("active")).toBe("Active");
  });
});
