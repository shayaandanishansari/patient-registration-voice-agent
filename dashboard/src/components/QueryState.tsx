import type { ReactNode } from "react";

import { ApiError } from "@/lib/api";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <p role="status" className="py-10 text-center text-sm text-slate-500">
      {label}
    </p>
  );
}

export function ErrorMessage({ error }: { error: unknown }) {
  const message =
    error instanceof ApiError
      ? error.status === 401
        ? "Your API key was rejected. Sign out and try again."
        : error.message
      : "Couldn't reach the API. Check your connection and try again.";
  return (
    <p role="alert" className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {message}
    </p>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-10 text-center text-sm text-slate-500">{children}</p>;
}
