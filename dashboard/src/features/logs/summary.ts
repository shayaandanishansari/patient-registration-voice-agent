import type { LogEntry } from "./types";

const MAX_VALUE = 60;

function short(value: unknown): string {
  const text = String(value);
  return text.length > MAX_VALUE ? `${text.slice(0, MAX_VALUE)}…` : text;
}

/** One line describing a log record, shown next to its event name. */
export function summarize(entry: LogEntry): string {
  const fields = entry.fields ?? {};
  if (!entry.event) return short(entry.message ?? "");

  if (entry.event === "http_request") {
    return `${fields.method} ${fields.path} → ${fields.status} · ${fields.duration_ms}ms`;
  }
  if (entry.event === "retell_tool") {
    const response = (fields.response ?? {}) as Record<string, unknown>;
    const outcome = response.status ?? response.verification_result;
    return `${fields.tool}${outcome ? ` → ${outcome}` : ""} · ${fields.call_id}`;
  }

  // Everything else: the scalar fields as key=value. Objects (payloads,
  // webhook bodies) only show when the row is expanded.
  return Object.entries(fields)
    .filter(([, value]) => value !== null && typeof value !== "object")
    .map(([key, value]) => `${key}=${short(value)}`)
    .join("  ");
}
