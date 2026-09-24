// The logs page's time window. It lives in the URL as either ?last=24h
// (relative: m, h, d or mo) or ?from=...&to=... (absolute, as
// <input type="datetime-local"> values in the viewer's time zone).

export const UNITS = { m: "minute", h: "hour", d: "day", mo: "month" } as const;
export type Unit = keyof typeof UNITS;

export type TimeRange =
  | { kind: "last"; amount: number; unit: Unit }
  | { kind: "between"; from?: string; to?: string };

export const PRESETS: { label: string; amount: number; unit: Unit }[] = [
  { label: "15m", amount: 15, unit: "m" },
  { label: "1h", amount: 1, unit: "h" },
  { label: "24h", amount: 24, unit: "h" },
  { label: "7d", amount: 7, unit: "d" },
  { label: "30d", amount: 30, unit: "d" },
  { label: "3mo", amount: 3, unit: "mo" },
];

export const DEFAULT_RANGE: TimeRange = { kind: "last", amount: 24, unit: "h" };

export function parseLast(value: string | null): TimeRange | null {
  const match = /^(\d+)(mo|m|h|d)$/.exec(value ?? "");
  if (!match || Number(match[1]) < 1) return null;
  return { kind: "last", amount: Number(match[1]), unit: match[2] as Unit };
}

export function rangeFromParams(params: URLSearchParams): TimeRange {
  const from = params.get("from") || undefined;
  const to = params.get("to") || undefined;
  if (from || to) return { kind: "between", from, to };
  return parseLast(params.get("last")) ?? DEFAULT_RANGE;
}

export function rangeToParams(range: TimeRange): [string, string][] {
  if (range.kind === "last") return [["last", `${range.amount}${range.unit}`]];
  return [
    ["from", range.from ?? ""],
    ["to", range.to ?? ""],
  ].filter(([, value]) => value) as [string, string][];
}

export function sameRange(a: TimeRange, b: TimeRange): boolean {
  return JSON.stringify(rangeToParams(a)) === JSON.stringify(rangeToParams(b));
}

/** The API's since/until (UTC ISO) for a range, anchored at `now`. */
export function resolveRange(
  range: TimeRange,
  now: Date = new Date(),
): { since?: string; until?: string } {
  if (range.kind === "between") {
    return {
      since: range.from ? new Date(range.from).toISOString() : undefined,
      until: range.to ? new Date(range.to).toISOString() : undefined,
    };
  }
  const since = new Date(now);
  if (range.unit === "m") since.setMinutes(since.getMinutes() - range.amount);
  if (range.unit === "h") since.setHours(since.getHours() - range.amount);
  if (range.unit === "d") since.setDate(since.getDate() - range.amount);
  if (range.unit === "mo") since.setMonth(since.getMonth() - range.amount);
  return { since: since.toISOString() };
}

function formatLocal(value: string): string {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function describeRange(range: TimeRange): string {
  if (range.kind === "last") {
    const unit = UNITS[range.unit];
    return `Last ${range.amount} ${unit}${range.amount === 1 ? "" : "s"}`;
  }
  return `${range.from ? formatLocal(range.from) : "The beginning"} → ${
    range.to ? formatLocal(range.to) : "now"
  }`;
}
