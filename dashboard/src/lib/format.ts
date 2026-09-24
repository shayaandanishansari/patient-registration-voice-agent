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
