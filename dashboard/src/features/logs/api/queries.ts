import { keepPreviousData, useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { getOne, getPage } from "@/lib/api";

import type { LogEntry, LogFilters } from "../types";

const PAGE_SIZE = 50;

export function useLogs(bounds: { since?: string; until?: string }, filters: LogFilters) {
  return useInfiniteQuery({
    queryKey: ["logs", bounds, filters],
    queryFn: ({ pageParam }) =>
      getPage<LogEntry>("/logs", { ...bounds, ...filters, limit: PAGE_SIZE, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    // Keep showing the current rows while a new filter loads.
    placeholderData: keepPreviousData,
  });
}

export function useLogEvents() {
  return useQuery({
    queryKey: ["log-events"],
    queryFn: () => getOne<string[]>("/logs/events"),
    staleTime: 60_000,
  });
}

/** The newest records, without per-request noise (the homepage preview). */
export function useRecentLogs(limit: number) {
  return useQuery({
    queryKey: ["logs", "recent", limit],
    queryFn: () => getPage<LogEntry>("/logs", { hide_http: true, limit }),
    refetchInterval: 15_000,
  });
}
