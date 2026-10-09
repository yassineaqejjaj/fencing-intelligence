import { describe, expect, it } from "vitest";
import { formatRate } from "./format";

describe("formatRate", () => {
  it("does not present a missing rate as zero", () => {
    expect(formatRate({ value: null, numerator: 0, denominator: 0, reason: "no_samples" })).toBe("—");
  });

  it("formats a real rate", () => {
    expect(formatRate({ value: 0.5, numerator: 1, denominator: 2, reason: null })).toBe("50.0%");
  });
});
