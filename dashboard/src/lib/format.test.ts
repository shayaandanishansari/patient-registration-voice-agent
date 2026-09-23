import { describe, expect, it } from "vitest";

import { formatDob, formatDuration, formatPhone } from "./format";

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
});
