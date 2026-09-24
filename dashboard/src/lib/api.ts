import type { components } from "@/types/api";

import { COOKIE_AUTH, getApiKey } from "./apiKey";

const RAILWAY_URL = "https://patient-registration-voice-agent-production-f401.up.railway.app";

// Served by the backend itself (the "embedded" build at /dashboard/): call the
// same server. Standalone: VITE_API_BASE_URL, else the Railway deployment.
export const API_BASE_URL: string =
  import.meta.env.MODE === "embedded"
    ? window.location.origin
    : import.meta.env.VITE_API_BASE_URL || RAILWAY_URL;

type ErrorBody = components["schemas"]["ApiError"];
export type ListMeta = components["schemas"]["ListMeta"];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

type Params = Record<string, string | number | boolean | null | undefined>;

function buildUrl(path: string, params?: Params): string {
  const url = new URL(path, API_BASE_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

// Every backend response is {"data": ..., "error": ...} (plus "meta" on
// lists). Unwrap it here so hooks and components only ever see data or a
// thrown ApiError.
async function request<T>(path: string, params?: Params): Promise<{ data: T; meta?: ListMeta }> {
  const response = await fetch(buildUrl(path, params), {
    headers: COOKIE_AUTH ? {} : { "x-api-key": getApiKey() ?? "" },
  });
  const body = (await response.json().catch(() => null)) as {
    data: T;
    error: ErrorBody | null;
    meta?: ListMeta;
  } | null;

  if (!response.ok || !body || body.error) {
    throw new ApiError(
      response.status,
      body?.error?.code ?? "network_error",
      body?.error?.message ?? `Request failed (${response.status}).`,
    );
  }
  return { data: body.data, meta: body.meta };
}

export async function getOne<T>(path: string, params?: Params): Promise<T> {
  return (await request<T>(path, params)).data;
}

export async function getPage<T>(
  path: string,
  params?: Params,
): Promise<{ items: T[]; nextCursor: string | null }> {
  const { data, meta } = await request<T[]>(path, params);
  return { items: data, nextCursor: meta?.next_cursor ?? null };
}
