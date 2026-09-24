import { describe, expect, it } from "vitest";

import { formatAgo, formatDob, formatDuration, formatPhone } from "./format";

describe("format", () => {
  it("formats 10-digit phone numbers", () => {
    expect(formatPhone("5125550123")).toBe("(512) 555-0123");
    expect(formatPhone(null)).toBe("—");
  });

  it("shows DOB as MM/DD/YYYY", () => {
    expect(formatDob("1990-03-05")).toBe("03/05/1990");
  });

  it("formats call durations", () => {
    expect(formatDuration(125_000)).toBe("2m 05s");
  });

  it("shows recent times relative to now", () => {
    const now = new Date("2026-09-24T12:00:00Z");
    expect(formatAgo("2026-09-24T11:59:40Z", now)).toBe("just now");
    expect(formatAgo("2026-09-24T11:55:00Z", now)).toBe("5m ago");
    expect(formatAgo("2026-09-24T09:00:00Z", now)).toBe("3h ago");
    expect(formatAgo(null, now)).toBe("—");
  });
});
