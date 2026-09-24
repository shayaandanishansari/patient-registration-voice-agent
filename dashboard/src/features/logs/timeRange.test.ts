import { describe, expect, it } from "vitest";

import { describeRange, parseLast, rangeFromParams, rangeToParams, resolveRange } from "./timeRange";

describe("timeRange", () => {
  it("parses relative ranges and rejects nonsense", () => {
    expect(parseLast("15m")).toEqual({ kind: "last", amount: 15, unit: "m" });
    expect(parseLast("3mo")).toEqual({ kind: "last", amount: 3, unit: "mo" });
    expect(parseLast("0d")).toBeNull();
    expect(parseLast("5y")).toBeNull();
  });

  it("defaults to the last 24 hours and round-trips through the URL", () => {
    expect(rangeFromParams(new URLSearchParams())).toEqual({ kind: "last", amount: 24, unit: "h" });
    const between = { kind: "between", from: "2026-09-01T09:00", to: "2026-09-02T17:30" } as const;
    expect(rangeFromParams(new URLSearchParams(rangeToParams(between)))).toEqual(between);
  });

  it("resolves relative ranges from a fixed now, months by the calendar", () => {
    const now = new Date("2026-09-24T12:00:00Z");
    expect(resolveRange({ kind: "last", amount: 1, unit: "h" }, now)).toEqual({
      since: "2026-09-24T11:00:00.000Z",
    });
    const threeMonths = resolveRange({ kind: "last", amount: 3, unit: "mo" }, now).since!;
    expect(threeMonths.slice(0, 7)).toBe("2026-06");
  });

  it("leaves an open end of an absolute range unset", () => {
    const { since, until } = resolveRange({ kind: "between", from: "2026-09-01T09:00" });
    expect(since).toBe(new Date("2026-09-01T09:00").toISOString());
    expect(until).toBeUndefined();
  });

  it("describes ranges for the list header", () => {
    expect(describeRange({ kind: "last", amount: 1, unit: "d" })).toBe("Last 1 day");
    expect(describeRange({ kind: "last", amount: 3, unit: "mo" })).toBe("Last 3 months");
    expect(describeRange({ kind: "between", from: "2026-09-01T09:00" })).toMatch(/→ now$/);
  });
});
