export function formatPhone(digits: string | null | undefined): string {
  if (!digits) return "—";
  if (digits.length !== 10) return digits;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
}

/** "1990-03-05" -> "03/05/1990" (the format the field spec uses). */
export function formatDob(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${month}/${day}/${year}`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatDuration(ms: number | null | undefined): string {
  if (!ms) return "—";
  const seconds = Math.round(ms / 1000);
  return `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
}

export function dash(value: string | null | undefined): string {
  return value ? value : "—";
}

/** For optional fields the caller may simply not have given. */
export function optional(value: string | null | undefined): string {
  return value ? value : "Not provided";
}

/** "just now", "5m ago", "3h ago", then the date for anything older than a day. */
export function formatAgo(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "—";
  const minutes = Math.floor((now.getTime() - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 24 * 60) return `${Math.floor(minutes / 60)}h ago`;
  return formatDateTime(iso);
}

/** Retell reports costs in cents: 10.28 -> "$0.10". */
export function formatCents(cents: number | null | undefined): string {
  if (cents == null) return "—";
  return `$${(cents / 100).toFixed(2)}`;
}
