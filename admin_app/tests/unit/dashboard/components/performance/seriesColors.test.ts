import { SERIES_COLORS } from "@/components/features/dashboard/components/performance/seriesColors";

describe("SERIES_COLORS", () => {
  it("has five distinct hex colours starting with the brand chart blue", () => {
    expect(SERIES_COLORS).toHaveLength(5);
    expect(new Set(SERIES_COLORS).size).toBe(5);
    SERIES_COLORS.forEach((c) => expect(c).toMatch(/^#[0-9A-F]{6}$/i));
    expect(SERIES_COLORS[0]).toBe("#264D96");
  });
});
